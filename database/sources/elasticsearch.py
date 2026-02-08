"""
Elasticsearch/OpenSearch Connector - For log and document queries
"""
from typing import Optional, Any


class ElasticsearchConnector:
    """
    Elasticsearch / OpenSearch Connector
    
    Dependencies:
        pip install elasticsearch[async]
    
    For OpenSearch:
        pip install opensearch-py
    
    Usage:
        connector = ElasticsearchConnector(
            hosts=["http://localhost:9200"],
            username="elastic",
            password="password"
        )
        await connector.connect()
        result = await connector.search("logs-*", {"match": {"level": "error"}})
    
    Note: This connector uses Elasticsearch DSL queries, not SQL.
    For SQL-like queries, use the SQL plugin if available.
    """
    
    def __init__(
        self,
        hosts: list[str] = None,
        username: str = "",
        password: str = "",
        use_ssl: bool = False,
        verify_certs: bool = True,
        use_opensearch: bool = False
    ):
        self.hosts = hosts or ["http://localhost:9200"]
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.verify_certs = verify_certs
        self.use_opensearch = use_opensearch
        self._client = None
    
    async def connect(self):
        """Create Elasticsearch client"""
        if self.use_opensearch:
            await self._connect_opensearch()
        else:
            await self._connect_elasticsearch()
    
    async def _connect_elasticsearch(self):
        """Connect to Elasticsearch"""
        try:
            from elasticsearch import AsyncElasticsearch
            
            self._client = AsyncElasticsearch(
                hosts=self.hosts,
                basic_auth=(self.username, self.password) if self.username else None,
                verify_certs=self.verify_certs
            )
        except ImportError:
            raise ImportError("elasticsearch is required. Install with: pip install elasticsearch[async]")
    
    async def _connect_opensearch(self):
        """Connect to OpenSearch"""
        try:
            from opensearchpy import AsyncOpenSearch
            
            self._client = AsyncOpenSearch(
                hosts=self.hosts,
                http_auth=(self.username, self.password) if self.username else None,
                verify_certs=self.verify_certs
            )
        except ImportError:
            raise ImportError("opensearch-py is required. Install with: pip install opensearch-py")
    
    async def disconnect(self):
        """Close client connection"""
        if self._client:
            await self._client.close()
            self._client = None
    
    async def search(
        self,
        index: str,
        query: dict,
        size: int = 100,
        sort: list = None
    ) -> dict:
        """
        Execute search query
        
        Args:
            index: Index pattern (e.g., "logs-*")
            query: Elasticsearch query DSL
            size: Number of results
            sort: Sort specification
        
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
    
    async def execute_sql(self, sql: str) -> dict:
        """
        Execute SQL query using Elasticsearch SQL plugin
        
        Note: Requires Elasticsearch with SQL plugin enabled
        """
        if not self._client:
            await self.connect()
        
        try:
            response = await self._client.sql.query(body={"query": sql})
            
            columns = [col["name"] for col in response.get("columns", [])]
            rows = response.get("rows", [])
            
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
    
    async def test_connection(self) -> bool:
        """Test connection to Elasticsearch"""
        try:
            if not self._client:
                await self.connect()
            await self._client.info()
            return True
        except Exception:
            return False
    
    # Helper methods for common queries
    
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
