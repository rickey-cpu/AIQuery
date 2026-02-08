import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from rag.opensearch_store import OpenSearchStore
from config import load_config_from_env

def migrate():
    load_config_from_env()
    store = OpenSearchStore()
    
    print("Step 1: Fetching existing definitions...")
    try:
        # Fetch all documents using match_all
        # Note: In a production system with millions of docs, we'd use scroll API
        # Here we assume < 10000 docs
        response = store.client.search(
            index=store.indices["semantic_definitions"],
            body={"query": {"match_all": {}}, "size": 10000}
        )
        hits = response["hits"]["hits"]
        print(f"Found {len(hits)} existing definitions.")
    except Exception as e:
        print(f"Error fetching docs (maybe index doesn't exist?): {e}")
        hits = []

    if not hits:
        print("No data to migrate. Initializing new index...")
    
    docs_to_restore = []
    for hit in hits:
        source = hit["_source"]
        # source has 'text', 'name', 'type', 'description', 'agent_id'
        # add_definitions expects keys: 'text', 'sql' (mapped to name), 'type', 'description'
        docs_to_restore.append({
            "text": source.get("text"),
            "sql": source.get("name"),
            "type": source.get("type"),
            "description": source.get("description"),
            "_agent_id": source.get("agent_id") # Temporary storage to pass to add_definitions loop
        })

    print("Step 2: Deleting old index to update mapping...")
    try:
        store.client.indices.delete(index=store.indices["semantic_definitions"])
        print("Old index deleted.")
    except Exception as e:
        print(f"Error deleting index: {e}")

    # Step 3: Re-initialize store to trigger _ensure_indices with NEW mapping
    print("Step 3: Re-creating index with KNN mapping...")
    store = OpenSearchStore()
    
    # Step 4: Re-ingest
    print(f"Step 4: Re-indexing {len(docs_to_restore)} documents (generating embeddings)...")
    
    # Group by agent_id for efficiency
    from collections import defaultdict
    grouped = defaultdict(list)
    for doc in docs_to_restore:
        aid = doc.pop("_agent_id", "system")
        grouped[aid].append(doc)
        
    for agent_id, docs in grouped.items():
        print(f"Processing {len(docs)} docs for agent: {agent_id}...")
        store.add_definitions(docs, agent_id=agent_id)
        
    print("✅ Migration complete! Semantic definitions now have vectors.")

if __name__ == "__main__":
    migrate()
