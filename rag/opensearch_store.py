"""
OpenSearch Connector for Semantic Layer
"""
from typing import List, Dict, Any, Optional
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
import boto3
from config import config

class OpenSearchStore:
    """
    OpenSearch Store for Semantic Layer
    Handles connection and semantic search operations
    """
    
    def __init__(self):
        self.client = self._create_client()
        self.indices = {
            "semantic_definitions": "semantic_definitions",
            "semantic_terms": "semantic_terms"
        }
        self._ensure_indices()

    def _create_client(self) -> OpenSearch:
        """Create OpenSearch client based on config"""
        auth = (config.opensearch.username, config.opensearch.password)
        
        if config.opensearch.use_aws_auth:
            credentials = boto3.Session().get_credentials()
            auth = AWSV4SignerAuth(credentials, config.opensearch.aws_region, config.opensearch.aws_service)

        return OpenSearch(
            hosts=config.opensearch.hosts,
            http_auth=auth,
            use_ssl=config.opensearch.use_ssl,
            verify_certs=config.opensearch.verify_certs,
            connection_class=RequestsHttpConnection,
            timeout=config.opensearch.timeout
        )

    def _ensure_indices(self):
        """Create indices if they don't exist"""
        # Schema for semantic definitions (Metrics/Entities)
        def_body = {
            "settings": {
                "index": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0
                }
            },
            "mappings": {
                "properties": {
                    "text": {"type": "text", "analyzer": "standard"},
                    "name": {"type": "keyword"},
                    "type": {"type": "keyword"},
                    "description": {"type": "text"},
                    # We can add knn_vector type here if we want embeddings later
                    # "embedding": {"type": "knn_vector", "dimension": 384} 
                }
            }
        }
        
        if not self.client.indices.exists(index=self.indices["semantic_definitions"]):
            self.client.indices.create(index=self.indices["semantic_definitions"], body=def_body)

    def add_definitions(self, definitions: List[Dict[str, Any]]):
        """Add definitions to OpenSearch"""
        if not definitions:
            return

        # Bulk insert
        body = ""
        for d in definitions:
            action = {"index": {"_index": self.indices["semantic_definitions"]}}
            body += str(action).replace("'", '"') + "\n"
            data = {
                "text": d.get("text", ""),
                "name": d.get("sql", ""), # Mapping 'sql' to 'name' for consistency with VectorStore interface
                "type": d.get("type", "unknown"),
                "description": d.get("description", "")
            }
            body += str(data).replace("'", '"') + "\n"
            
        if body:
            self.client.bulk(body=body)
            self.client.indices.refresh(index=self.indices["semantic_definitions"])

    def search_definitions(self, query: str, k: int = 3) -> List[Dict]:
        """Search for definitions using fuzzy text match (or vector if enabled)"""
        # For now, using standard text search with fuzziness
        body = {
            "size": k,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["text^2", "description"],
                    "fuzziness": "AUTO"
                }
            }
        }
        
        response = self.client.search(index=self.indices["semantic_definitions"], body=body)
        
        results = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            results.append({
                "question": source.get("text"),
                "sql": source.get("name"),
                "type": source.get("type"),
                "score": hit["_score"]
            })
            
        return results

    def count(self) -> int:
        """Count documents in definitions index"""
        return self.client.count(index=self.indices["semantic_definitions"])["count"]
