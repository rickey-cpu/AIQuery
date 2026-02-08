import asyncio
import os
from dotenv import load_dotenv
from config import config, load_config_from_env
from rag.opensearch_store import OpenSearchStore
from agents.tools import ColumnFinderTool
from rag.semantic_layer import SemanticLayer, SemanticEntity, SemanticMetric

# Load environment variables
load_dotenv()
load_config_from_env()

# Set config to use OpenSearch (mocking env if needed or relying on .env)
# config.opensearch.hosts = ["http://localhost:9200"] 


async def test_opensearch_flow():
    print("\n=== Testing OpenSearch Integration ===")
    
    # 1. Initialize OpenSearch Store
    try:
        print(f"Debug Config: hosts={config.opensearch.hosts}, ssl={config.opensearch.use_ssl}, verify={config.opensearch.verify_certs}")
        print("Initializing OpenSearchStore...")
        store = OpenSearchStore()
        print("[OK] OpenSearchStore initialized.")
    except Exception as e:
        print(f"[ERROR] Failed to initialize OpenSearchStore: {e}")
        return

    # 2. Test Few-Shot Example Support
    print("\n--- Testing Few-Shot Examples ---")
    examples = [
        {"question": "test query", "sql": "SELECT 1", "description": "Test example"}
    ]
    try:
        store.add_examples(examples)
        print("[OK] Added test example.")
        
        results = store.search_similar("test query", k=1)
        if results and results[0]['sql'] == "SELECT 1":
            print(f"[OK] Search similar success: Found {len(results)} examples.")
            print(f"   Result: {results[0]}")
        else:
            print(f"[FAIL] Search similar failed: {results}")
            
    except Exception as e:
        print(f"[ERROR] Error in few-shot testing: {e}")

    # 3. Test Semantic Layer & Column Finder
    print("\n--- Testing Semantic Layer & Column Finder ---")
    try:
        sl = SemanticLayer()
        # Ensure we have data
        # Explicitly index to bypass "if empty" check in _sync_vector_store
        test_entity = SemanticEntity("TestUser", "users", "id", "A test user entity", ["test user"])
        sl.add_entity(test_entity)
        
        # Manually add to vector store
        sl.vector_store.add_definitions([{
            "text": f"Entity: {test_entity.name}. {test_entity.description}. Synonyms: {', '.join(test_entity.synonyms)}",
            "sql": test_entity.name,
            "type": "entity",
            "description": test_entity.description
        }])
        
        # Give it a moment to index if needed (though refresh=True usually handles it)
        await asyncio.sleep(2) 
        
        finder = ColumnFinderTool(semantic_layer=sl)
        
        print("Testing ColumnFinder with semantic term 'test user'...")
        columns = await finder._arun("test user")
        
        found = False
        for col in columns:
            print(f"  Found: {col.get('table')}.{col.get('column')} - {col.get('description')}")
            if col.get('table') == 'users':
                found = True
                
        if found:
            print("[OK] ColumnFinder successfully used OpenSearch semantic search.")
        else:
            print("[FAIL] ColumnFinder did not return expected OpenSearch result.")
            
    except Exception as e:
        print(f"[ERROR] Error in ColumnFinder testing: {e}")

if __name__ == "__main__":
    asyncio.run(test_opensearch_flow())
