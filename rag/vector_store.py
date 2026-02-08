"""
Vector Store - ChromaDB integration for SQL examples and few-shot learning
"""
import chromadb
from chromadb.config import Settings
from typing import Optional
from pathlib import Path

# Global vector store instance
_vector_store: Optional["VectorStore"] = None


class VectorStore:
    """
    Vector Store using ChromaDB
    
    Stores SQL examples for few-shot learning and similarity search
    Inspired by FINCH's RAG approach
    """
    
    def __init__(self, persist_directory: str = "./data/chroma", collection_name: str = "sql_examples"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "SQL examples for few-shot learning"}
        )
        
        # Seed with default examples if empty
        if self.collection.count() == 0:
            self._seed_default_examples()
    
    def _seed_default_examples(self):
        """Seed collection with default SQL examples"""
        examples = [
            # Basic SELECT
            {"question": "Show all customers", "sql": "SELECT * FROM customers LIMIT 100"},
            {"question": "List all products", "sql": "SELECT * FROM products LIMIT 100"},
            {"question": "Get all orders", "sql": "SELECT * FROM orders LIMIT 100"},
            
            # Filtering
            {"question": "Customers from Hanoi", "sql": "SELECT * FROM customers WHERE city = 'Hanoi'"},
            {"question": "Products under 100 dollar", "sql": "SELECT * FROM products WHERE price < 100"},
            {"question": "Orders from last month", "sql": "SELECT * FROM orders WHERE order_date >= date('now', '-1 month')"},
            
            # Aggregations
            {"question": "Total revenue", "sql": "SELECT SUM(total_amount) as total_revenue FROM orders"},
            {"question": "Number of customers", "sql": "SELECT COUNT(*) as customer_count FROM customers"},
            {"question": "Average order value", "sql": "SELECT AVG(total_amount) as avg_order_value FROM orders"},
            
            # Grouping
            {"question": "Revenue by month", "sql": "SELECT strftime('%Y-%m', order_date) as month, SUM(total_amount) as revenue FROM orders GROUP BY month ORDER BY month"},
            {"question": "Orders by status", "sql": "SELECT status, COUNT(*) as count FROM orders GROUP BY status"},
            {"question": "Top selling products", "sql": "SELECT p.name, SUM(oi.quantity) as total_sold FROM products p JOIN order_items oi ON p.id = oi.product_id GROUP BY p.id ORDER BY total_sold DESC LIMIT 10"},
            
            # Joins
            {"question": "Customer orders with details", "sql": "SELECT c.name, o.id, o.total_amount, o.order_date FROM customers c JOIN orders o ON c.id = o.customer_id ORDER BY o.order_date DESC LIMIT 50"},
            {"question": "Product categories with counts", "sql": "SELECT c.name as category, COUNT(p.id) as product_count FROM categories c LEFT JOIN products p ON c.id = p.category_id GROUP BY c.id"},
        ]
        
        self.add_examples(examples)
    
    def add_examples(self, examples: list[dict]):
        """Add SQL examples to the vector store"""
        if not examples:
            return
        
        documents = [ex["question"] for ex in examples]
        metadatas = [{"sql": ex["sql"]} for ex in examples]
        ids = [f"ex_{i}_{hash(ex['question']) % 10000}" for i, ex in enumerate(examples)]
        
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    def search_similar(self, question: str, k: int = 3) -> list[dict]:
        """Search for similar SQL examples"""
        results = self.collection.query(
            query_texts=[question],
            n_results=k
        )
        
        examples = []
        if results["documents"] and results["metadatas"]:
            for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                examples.append({
                    "question": doc,
                    "sql": meta.get("sql", "")
                })
        
        return examples
    
    def get_all_examples(self) -> list[dict]:
        """Get all examples in the store"""
        results = self.collection.get()
        
        examples = []
        if results["documents"] and results["metadatas"]:
            for doc, meta in zip(results["documents"], results["metadatas"]):
                examples.append({
                    "question": doc,
                    "sql": meta.get("sql", "")
                })
        
        return examples
    
    def clear(self):
        """Clear all examples"""
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.create_collection(
            name=self.collection.name,
            metadata={"description": "SQL examples for few-shot learning"}
        )



def init_vector_store():
    """Initialize global vector store"""
    global _vector_store
    from config import config
    
    # Check if OpenSearch is configured/preferred
    use_opensearch = False
    if hasattr(config, "opensearch") and config.opensearch.hosts:
        # Simple check: if hosts are defined, try to use it
        # You might want a stronger signal like config.vector_store.use_opensearch
        use_opensearch = True
        
    if use_opensearch:
        try:
            from .opensearch_store import OpenSearchStore
            _vector_store = OpenSearchStore()
            print("Vector Store: Initialized OpenSearchStore")
            
            # Seed default examples if empty
            # Note: OpenSearchStore implementation of count() might need to check sql_examples index
            # For now, we'll skip auto-seeding or rely on a specific method
            return _vector_store
        except Exception as e:
            print(f"Failed to initialize OpenSearchStore: {e}")
            print("Falling back to ChromaDB")

    _vector_store = VectorStore(
        persist_directory=config.vector_store.persist_directory,
        collection_name=config.vector_store.collection_name
    )
    print("Vector Store: Initialized ChromaDB")
    return _vector_store


def get_vector_store():
    """Get global vector store instance"""
    global _vector_store
    if _vector_store is None:
        return init_vector_store()
    return _vector_store
