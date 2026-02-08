import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from rag.opensearch_store import OpenSearchStore
from config import load_config_from_env

def verify_vector_search():
    load_config_from_env()
    store = OpenSearchStore()
    
    # 1. Check if model is loaded
    if not store.embedding_model:
        print("[FAIL] Embedding model not loaded!")
        return

    print("[OK] Embedding model loaded.")

    # 2. Check mapping
    try:
        mapping = store.client.indices.get_mapping(index="semantic_definitions")
        props = mapping["semantic_definitions"]["mappings"]["properties"]
        if "embedding" in props and props["embedding"]["type"] == "knn_vector":
            print("[OK] Index mapping has knn_vector field.")
        else:
            print("[FAIL] Index mapping missing knn_vector field.")
            print(props)
            return
    except Exception as e:
        print(f"[FAIL] Error checking mapping: {e}")
        return

    # 3. Perform Hybrid Search
    query = "people living in cities"
    print(f"\nSearching for: '{query}'")
    results = store.search_definitions(query, k=3, agent_id="WorldExplorer")
    
    if not results:
        print("[WARN] No results found. Did you populate data?")
        return

    print(f"Found {len(results)} results:")
    for res in results:
        print(f" - {res['sql']} ({res['type']}) [Score: {res['score']:.4f}]")
        print(f"   Desc: {res['question'][:50]}...")

    # Validate that we got reasonable results
    # "people living in cities" should match "Population" metric or "City" entity
    found_relevant = any(r['sql'] in ['Population', 'City'] for r in results)
    if found_relevant:
        print("[OK] Relevant results found via hybrid search.")
    else:
        print("[WARN] Query didn't return expected top hits. Check embeddings.")

if __name__ == "__main__":
    verify_vector_search()
