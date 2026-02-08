"""
OpenSearch Connector - Dedicated connector for OpenSearch with specific features
"""
from typing import Optional, Any


class OpenSearchConnector:
    """
    OpenSearch Connector with OpenSearch-specific features
    
    Dependencies:
        pip install opensearch-py
    
    Features:
        - Async client support
        - PPL (Piped Processing Language) queries
        - SQL queries via SQL plugin
        - k-NN vector search
        - AWS OpenSearch Service authentication
    
    Usage:
        connector = OpenSearchConnector(
            hosts=["http://localhost:9200"],
            username="admin",
            password="admin"
        )
        await connector.connect()
        result = await connector.search("logs-*", {"match": {"level": "error"}})
    """
    
    def __init__(
        self,
        hosts: list[str] = None,
        username: str = "",
        password: str = "",
        use_ssl: bool = False,
        verify_certs: bool = True,
        aws_region: str = "",
        aws_service: str = "es",  # 'es' for OpenSearch Service, 'aoss' for Serverless
        use_aws_auth: bool = False,
        timeout: int = 30
    ):
        self.hosts = hosts or ["http://localhost:9200"]
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.verify_certs = verify_certs
        self.aws_region = aws_region
        self.aws_service = aws_service
        self.use_aws_auth = use_aws_auth
        self.timeout = timeout
        self._client = None
    
    async def connect(self):
        """Create OpenSearch async client"""
        try:
            from opensearchpy import AsyncOpenSearch
            
            if self.use_aws_auth:
                self._client = await self._connect_with_aws_auth()
            else:
                auth = (self.username, self.password) if self.username else None
                self._client = AsyncOpenSearch(
                    hosts=self.hosts,
                    http_auth=auth,
                    use_ssl=self.use_ssl,
                    verify_certs=self.verify_certs,
                    timeout=self.timeout
                )
        except ImportError:
            raise ImportError("opensearch-py is required. Install with: pip install opensearch-py")
    
    async def _connect_with_aws_auth(self):
        """Connect using AWS authentication (SigV4)"""
        try:
            from opensearchpy import AsyncOpenSearch, AWSV4SignerAuth
            import boto3
            
            credentials = boto3.Session().get_credentials()
            auth = AWSV4SignerAuth(credentials, self.aws_region, self.aws_service)
            
            return AsyncOpenSearch(
                hosts=self.hosts,
                http_auth=auth,
                use_ssl=True,
                verify_certs=True,
                timeout=self.timeout
            )
        except ImportError as e:
            raise ImportError(f"boto3 is required for AWS auth. Install with: pip install boto3. Error: {e}")
    
    async def disconnect(self):
        """Close client connection"""
        if self._client:
            await self._client.close()
            self._client = None
    
    async def test_connection(self) -> bool:
        """Test connection to OpenSearch"""
        try:
            if not self._client:
                await self.connect()
            await self._client.info()
            return True
        except Exception:
            return False
    
    # ==================== Search Operations ====================
    
    async def search(
        self,
        index: str,
        query: dict,
        size: int = 100,
        sort: list = None,
        source: list = None
    ) -> dict:
        """
        Execute search query using OpenSearch DSL
        
        Args:
            index: Index pattern (e.g., "logs-*")
            query: OpenSearch query DSL
            size: Number of results
            sort: Sort specification
            source: Fields to include in response
        
        Returns:
            Dict with columns, rows, row_count
        """
        if not self._client:
            await self.connect()
        
        body = {
            "query": query,
            "size": size
        }
        if sort:
            body["sort"] = sort
        if source:
            body["_source"] = source
        
        response = await self._client.search(index=index, body=body)
        
        hits = response["hits"]["hits"]
        
        if not hits:
            return {"columns": [], "rows": [], "row_count": 0}
        
        # Extract columns from first hit
        first_source = hits[0]["_source"]
        columns = list(first_source.keys())
        
        # Extract rows
        rows = []
        for hit in hits:
            source = hit["_source"]
            row = [source.get(col) for col in columns]
            rows.append(row)
        
        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "total": response["hits"]["total"]["value"]
        }
    
    # ==================== SQL Plugin ====================
    
    async def execute_sql(self, sql: str, fetch_size: int = 200) -> dict:
        """
        Execute SQL query using OpenSearch SQL plugin
        
        Note: Requires OpenSearch SQL plugin enabled
        Docs: https://opensearch.org/docs/latest/search-plugins/sql/
        """
        if not self._client:
            await self.connect()
        
        try:
            response = await self._client.transport.perform_request(
                "POST",
                "/_plugins/_sql",
                body={"query": sql, "fetch_size": fetch_size}
            )
            
            columns = [col["name"] for col in response.get("schema", [])]
            rows = response.get("datarows", [])
            
            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows)
            }
        except Exception as e:
            return {
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": str(e)
            }
    
    # ==================== PPL (Piped Processing Language) ====================
    
    async def execute_ppl(self, ppl_query: str) -> dict:
        """
        Execute PPL query
        
        PPL Example:
            source=logs | where level='error' | stats count() by host
        
        Docs: https://opensearch.org/docs/latest/search-plugins/sql/ppl/
        """
        if not self._client:
            await self.connect()
        
        try:
            response = await self._client.transport.perform_request(
                "POST",
                "/_plugins/_ppl",
                body={"query": ppl_query}
            )
            
            columns = [col["name"] for col in response.get("schema", [])]
            rows = response.get("datarows", [])
            
            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows)
            }
        except Exception as e:
            return {
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": str(e)
            }
    
    # ==================== k-NN Vector Search ====================
    
    async def knn_search(
        self,
        index: str,
        field: str,
        vector: list[float],
        k: int = 10,
        filter_query: dict = None
    ) -> dict:
        """
        Execute k-NN vector search
        
        Args:
            index: Index with k-NN enabled
            field: Vector field name
            vector: Query vector
            k: Number of nearest neighbors
            filter_query: Optional filter query
        
        Docs: https://opensearch.org/docs/latest/search-plugins/knn/
        """
        if not self._client:
            await self.connect()
        
        knn_query = {
            "knn": {
                field: {
                    "vector": vector,
                    "k": k
                }
            }
        }
        
        if filter_query:
            knn_query["knn"][field]["filter"] = filter_query
        
        body = {
            "size": k,
            "query": knn_query
        }
        
        response = await self._client.search(index=index, body=body)
        
        hits = response["hits"]["hits"]
        results = []
        for hit in hits:
            results.append({
                "_id": hit["_id"],
                "_score": hit["_score"],
                **hit["_source"]
            })
        
        return {
            "results": results,
            "total": response["hits"]["total"]["value"]
        }
    
    # ==================== Index Operations ====================
    
    async def get_indices(self) -> list[str]:
        """Get list of indices"""
        if not self._client:
            await self.connect()
        
        indices = await self._client.cat.indices(format="json")
        return [idx["index"] for idx in indices if not idx["index"].startswith(".")]
    
    async def get_mapping(self, index: str) -> dict:
        """Get index mapping (schema)"""
        if not self._client:
            await self.connect()
        
        mapping = await self._client.indices.get_mapping(index=index)
        
        # Extract field names and types
        fields = []
        for idx_name, idx_mapping in mapping.items():
            properties = idx_mapping.get("mappings", {}).get("properties", {})
            for field_name, field_info in properties.items():
                fields.append({
                    "column": field_name,
                    "type": field_info.get("type", "unknown")
                })
        
        return fields
    
    async def get_cluster_info(self) -> dict:
        """Get OpenSearch cluster information"""
        if not self._client:
            await self.connect()
        
        info = await self._client.info()
        return {
            "name": info.get("cluster_name"),
            "version": info.get("version", {}).get("number"),
            "distribution": info.get("version", {}).get("distribution", "opensearch")
        }
    
    # ==================== Helper Query Methods ====================
    
    async def match_query(self, index: str, field: str, value: str, size: int = 100) -> dict:
        """Execute a simple match query"""
        return await self.search(index, {"match": {field: value}}, size)
    
    async def term_query(self, index: str, field: str, value: Any, size: int = 100) -> dict:
        """Execute a term query (exact match)"""
        return await self.search(index, {"term": {field: value}}, size)
    
    async def range_query(
        self,
        index: str,
        field: str,
        gte: Any = None,
        lte: Any = None,
        size: int = 100
    ) -> dict:
        """Execute a range query"""
        range_spec = {}
        if gte is not None:
            range_spec["gte"] = gte
        if lte is not None:
            range_spec["lte"] = lte
        
        return await self.search(index, {"range": {field: range_spec}}, size)
    
    async def aggregate(
        self,
        index: str,
        agg_name: str,
        agg_type: str,
        field: str,
        query: dict = None
    ) -> dict:
        """
        Execute aggregation query
        
        Args:
            agg_type: "sum", "avg", "min", "max", "count", "terms"
        """
        if not self._client:
            await self.connect()
        
        body = {
            "size": 0,
            "aggs": {
                agg_name: {agg_type: {"field": field}}
            }
        }
        if query:
            body["query"] = query
        
        response = await self._client.search(index=index, body=body)
        
        return {
            "aggregation": agg_name,
            "result": response["aggregations"][agg_name]
        }
