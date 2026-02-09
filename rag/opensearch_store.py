"""
OpenSearch Connector for Semantic Layer
"""
from typing import List, Dict, Any, Optional
import json
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
import boto3
from config import config
try:
    from sentence_transformers import SentenceTransformer
    HAS_EMBEDDINGS = True
except ImportError:
    HAS_EMBEDDINGS = False
    print("Warning: sentence-transformers not found. Vector search disabled.")

class OpenSearchStore:
    """
    OpenSearch Store for Semantic Layer
    Handles connection and semantic search operations (Hybrid: Keyword + Vector)
    """
    
    def __init__(self):
        self.client = self._create_client()
        self.indices = {
            "semantic_definitions": "semantic_definitions",
            "semantic_terms": "semantic_terms"
        }
        
        # Initialize embedding model if available
        self.embedding_model = None
        if HAS_EMBEDDINGS:
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                print(f"Failed to load embedding model: {e}")

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
                    "number_of_replicas": 0,
                    "knn": True  # Enable KNN
                }
            },
            "mappings": {
                "properties": {
                    "text": {"type": "text", "analyzer": "standard"},
                    "name": {"type": "keyword"},
                    "type": {"type": "keyword"},
                    "description": {"type": "text"},
                    "agent_id": {"type": "keyword"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 384,
                        "method": {
                            "name": "hnsw",
                            "engine": "nmslib",
                            "space_type": "cosinesimil"
                        }
                    }
                }
            }
        }
        
        if not self.client.indices.exists(index=self.indices["semantic_definitions"]):
            self.client.indices.create(index=self.indices["semantic_definitions"], body=def_body)

        # Schema for SQL examples (Few-shot)
        examples_body = {
            "settings": {
                "index": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "knn": True
                }
            },
            "mappings": {
                "properties": {
                    "question": {"type": "text", "analyzer": "standard"},
                    "sql": {"type": "text"},
                    "description": {"type": "text"},
                    "agent_id": {"type": "keyword"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 384,
                        "method": {
                            "name": "hnsw",
                            "engine": "nmslib",
                            "space_type": "cosinesimil"
                        }
                    }
                }
            }
        }

        if not self.client.indices.exists(index="sql_examples"):
            self.client.indices.create(index="sql_examples", body=examples_body)

    def _generate_id(self, name: str, type_: str, agent_id: str) -> str:
        """Generate deterministic ID for semantic definitions"""
        # ID format: agent_id_type_name (sanitized)
        safe_name = "".join(x for x in name if x.isalnum() or x in "-_")
        return f"{agent_id}_{type_}_{safe_name}"

    def add_definitions(self, definitions: List[Dict[str, Any]], agent_id: Optional[str] = None):
        """Add definitions to OpenSearch (Upsert)"""
        if not definitions:
            return

        effective_agent_id = agent_id or "system"
        
        # Batch size for bulk operations
        BATCH_SIZE = 100
        
        for i in range(0, len(definitions), BATCH_SIZE):
            chunk = definitions[i:i + BATCH_SIZE]
            body = ""
            
            for d in chunk:
                name = d.get("sql", "") # Using 'sql' as name/identifier
                type_ = d.get("type", "unknown")
                doc_id = self._generate_id(name, type_, effective_agent_id)
                
                text_content = d.get("text", "")
                
                # Generate embedding if not already present
                embedding = d.get("embedding") # Check if already in input
                if not embedding and self.embedding_model:
                    try:
                        embedding = self.embedding_model.encode(text_content).tolist()
                    except Exception as e:
                        print(f"Error generating embedding for {name}: {e}")

                action = {
                    "index": {
                        "_index": self.indices["semantic_definitions"],
                        "_id": doc_id
                    }
                }
                body += json.dumps(action) + "\n"
                
                data = {
                    "text": text_content,
                    "name": name, 
                    "type": type_,
                    "description": d.get("description", ""),
                    "agent_id": effective_agent_id
                }
                if embedding:
                    data["embedding"] = embedding
                    
                body += json.dumps(data) + "\n"
                
            if body:
                try:
                    self.client.bulk(body=body)
                except Exception as e:
                    print(f"Error in bulk indexing batch {i}: {e}")
            
            self.client.indices.refresh(index=self.indices["semantic_definitions"])

    def delete_definition(self, name: str, type_: str, agent_id: Optional[str] = None) -> bool:
        """Delete a definition by name and type"""
        effective_agent_id = agent_id or "system"
        doc_id = self._generate_id(name, type_, effective_agent_id)
        
        try:
            self.client.delete(
                index=self.indices["semantic_definitions"],
                id=doc_id,
                refresh=True
            )
            return True
        except Exception as e:
            print(f"Error deleting definition {doc_id}: {e}")
            return False

    def add_examples(self, examples: List[Dict[str, Any]], agent_id: Optional[str] = None):
        """Add SQL examples to OpenSearch (Few-shot)"""
        if not examples:
            return

        body = ""
        for ex in examples:
            action = {"index": {"_index": "sql_examples"}}
            body += json.dumps(action) + "\n"
            
            question = ex.get("question", "")
            
            # Generate embedding
            embedding = []
            if self.embedding_model:
                try:
                    embedding = self.embedding_model.encode(question).tolist()
                except Exception as e:
                    print(f"Error generating embedding for example: {e}")

            data = {
                "question": question,
                "sql": ex.get("sql", ""),
                "description": ex.get("description", ""),
                "agent_id": agent_id or "system"
            }
            if embedding:
                data["embedding"] = embedding

            body += json.dumps(data) + "\n"
            
        if body:
            self.client.bulk(body=body)
            self.client.indices.refresh(index="sql_examples")

    def search_definitions(self, query: str, k: int = 3, agent_id: Optional[str] = None) -> List[Dict]:
        """Search for definitions using Hybrid Search (Vector + Keyword)"""
        
        # 1. Keyword Query (Base)
        if query == "*":
             keyword_query = {"match_all": {}}
        else:
            keyword_query = {
                "multi_match": {
                    "query": query,
                    "fields": ["text^2", "description"],
                    "fuzziness": "AUTO"
                }
            }

        # 2. Vector Query (KNN)
        vector_query = None
        if self.embedding_model and query != "*":
            try:
                query_vector = self.embedding_model.encode(query).tolist()
                vector_query = {
                    "knn": {
                        "embedding": {
                            "vector": query_vector,
                            "k": k
                        }
                    }
                }
            except Exception as e:
                print(f"Error encoding query: {e}")

        # 3. Filter Context
        filters = []
        if agent_id:
             filters.append({"terms": {"agent_id": [agent_id, "system"]}})
        else:
             filters.append({"term": {"agent_id": "system"}})

        # 4. Construct Hybrid Query
        # If vector is available, we use 'should' to combine both signals
        # If query is '*', we rely on keyword_query (match_all)
        
        if vector_query:
            must_clause = [
                {
                    "bool": {
                        "should": [
                            keyword_query, 
                            vector_query
                        ],
                        "minimum_should_match": 1
                    }
                }
            ]
        else:
            must_clause = [keyword_query]

        body = {
            "size": k,
            "query": {
                "bool": {
                    "must": must_clause,
                    "filter": filters
                }
            }
        }
        
        try:
            response = self.client.search(index=self.indices["semantic_definitions"], body=body)
            
            results = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                results.append({
                    "question": source.get("text"),
                    "sql": source.get("name"),
                    "type": source.get("type"),
                    "score": hit["_score"],
                    "obj": None
                })
            return results
        except Exception as e:
            print(f"Search failed: {e}")
            return []

    def search_similar(self, question: str, k: int = 3, agent_id: Optional[str] = None) -> List[Dict]:
        """Search for similar SQL examples (Hybrid)"""
        
        # Keyword part
        keyword_query = {
            "match": {
                "question": {
                    "query": question,
                    "fuzziness": "AUTO"
                }
            }
        }
        
        # Vector part
        vector_query = None
        if self.embedding_model:
            try:
                query_vector = self.embedding_model.encode(question).tolist()
                vector_query = {
                    "knn": {
                        "embedding": {
                            "vector": query_vector,
                            "k": k
                        }
                    }
                }
            except Exception as e:
                print(f"Error encoding query: {e}")
        
        # Filters
        filters = []
        if agent_id:
             filters.append({"terms": {"agent_id": [agent_id, "system"]}})
        else:
             filters.append({"term": {"agent_id": "system"}})

        # Combine
        if vector_query:
            must_clause = [
                {
                    "bool": {
                        "should": [keyword_query, vector_query],
                        "minimum_should_match": 1
                    }
                }
            ]
        else:
            must_clause = [keyword_query]

        body = {
            "size": k,
            "query": {
                "bool": {
                    "must": must_clause,
                    "filter": filters
                }
            }
        }

        try:
            response = self.client.search(index="sql_examples", body=body)
            results = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                results.append({
                    "question": source.get("question"),
                    "sql": source.get("sql"),
                    "score": hit["_score"]
                })
            return results
        except Exception as e:
            print(f"Error searching examples: {e}")
            return []

    def count(self) -> int:
        """Count documents in definitions index"""
        return self.client.count(index=self.indices["semantic_definitions"])["count"]
