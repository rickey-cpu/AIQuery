
import asyncio
from rag.semantic_layer import SemanticLayer

def test_semantic_layer():
    print("Initializing Semantic Layer...")
    try:
        sl = SemanticLayer()
    except Exception as e:
        print(f"Failed to initialize Semantic Layer (likely OpenSearch connection error): {e}")
        return
    
    print("\n--- Testing Knowledge Graph ---")
    print("Entities:", list(sl.entities.keys()))
    print("Metrics:", list(sl.metrics.keys()))
    
    print("\n--- Testing Path Finding ---")
    path = sl.find_path("Customer", "OrderItem")
    print(f"Path Customer -> OrderItem: {len(path)} hops")
    for r in path:
        print(f"  {r.from_entity} <-> {r.to_entity} ON {r.join_condition}")
        
    print("\n--- Testing Vector Search ---")
    print("Searching for 'money generated'...")
    results = sl.search_definitions("money generated")
    for res in results:
        obj = res['obj']
        print(f"  Found {res['type']}: {obj.name} - {obj.description}")
        
    print("\n--- Testing Context Generation ---")
    context = sl.get_semantic_context("average order value")
    print("Context for 'average order value' (first 500 chars):")
    try:
        print(context[:500])
    except UnicodeEncodeError:
        print(context[:500].encode('utf-8', errors='ignore').decode('utf-8'))

if __name__ == "__main__":
    test_semantic_layer()
