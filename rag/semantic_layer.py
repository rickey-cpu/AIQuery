"""
Semantic Layer - Maps business terminology to SQL columns/values
Inspired by Uber FINCH's Semantic Layer with Knowledge Graph & Metrics
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
import json
from pathlib import Path
from .opensearch_store import OpenSearchStore

@dataclass
class SemanticEntity:
    """Represents a business entity mapped to a database table"""
    name: str  # Business name (e.g. "Customer")
    table_name: str  # SQL table (e.g. "customers")
    primary_key: str # PK column (e.g. "id")
    description: str # Description for LLM
    synonyms: List[str] = field(default_factory=list)

@dataclass
class SemanticMetric:
    """Represents a standardized business metric"""
    name: str # e.g. "Revenue"
    definition: str # SQL fragment, e.g. "SUM(total_amount)"
    description: str
    condition: Optional[str] = None # e.g. "status = 'completed'"
    synonyms: List[str] = field(default_factory=list)

@dataclass
class SemanticRelationship:
    """Represents a relationship between two entities (Knowledge Graph edge)"""
    from_entity: str
    to_entity: str
    join_condition: str # e.g. "orders.customer_id = customers.id"
    relation_type: str # "one_to_many", "many_to_one", "one_to_one"

@dataclass
class TermMapping:
    """Legacy term mapping (kept for backward compatibility/simple lookups)"""
    term: str
    sql_column: str
    table: str
    description: str = ""
    synonyms: List[str] = field(default_factory=list)

@dataclass
class ValueMapping:
    """Value alias mapping"""
    alias: str
    actual_value: str
    column: str
    table: str

class SemanticLayer:
    """
    Advanced Semantic Layer (Finch-grade)
    
    Features:
    - Knowledge Graph (Entities & Relationships)
    - Semantic Metrics (Standardized KPIs)
    - Vector-based Semantic Search (for mappings/metrics)
    - Legacy Term/Value Mapping support
    """
    
    def __init__(self, mappings_file: Optional[str] = None):
        self.entities: Dict[str, SemanticEntity] = {}
        self.metrics: Dict[str, SemanticMetric] = {}
        self.relationships: List[SemanticRelationship] = []
        
        self.term_mappings: List[TermMapping] = []
        self.value_mappings: List[ValueMapping] = []
        
        # Initialize dictionary-based indexes for fast lookup
        self._entity_map = {}

        # Load from file if provided
        if mappings_file and Path(mappings_file).exists():
            self.load_from_file(mappings_file)
        else:
            self._load_default_mappings()
            
        # Re-build index to be sure (or just rely on add_entity)
        self._entity_map = {e.name.lower(): e for e in self.entities.values()}
        for e in self.entities.values():
            for s in e.synonyms:
                self._entity_map[s.lower()] = e

        # Initialize OpenSearch Store for Semantic Definitions
        # We use a separate collection for semantic definitions
        self.vector_store = OpenSearchStore()
        self._sync_vector_store()

    def _sync_vector_store(self):
        """Sync metrics and entities to vector store if empty"""
        # Simple check if index is empty
        if self.vector_store.count() == 0:
            examples = []
            
            # Index Entities
            for e in self.entities.values():
                text = f"Entity: {e.name}. {e.description}. Synonyms: {', '.join(e.synonyms)}"
                examples.append({"text": text, "sql": e.name, "type": "entity"})
                
            # Index Metrics
            for m in self.metrics.values():
                text = f"Metric: {m.name}. {m.description}. Synonyms: {', '.join(m.synonyms)}"
                examples.append({"text": text, "sql": m.name, "type": "metric"})
            
            if examples:
                self.vector_store.add_definitions(examples)

    def search_definitions(self, query: str, k: int = 3) -> List[Dict]:
        """Search for relevant semantic definitions using vector store"""
        results = self.vector_store.search_definitions(query, k=k)
        # Enrich results with actual objects
        enriched = []
        for res in results:
            name = res.get('sql') # We stored name in 'sql' field for reuse
            if name in self.entities:
                enriched.append({"type": "entity", "obj": self.entities[name]})
            elif name in self.metrics:
                enriched.append({"type": "metric", "obj": self.metrics[name]})
        return enriched

    def _load_default_mappings(self):
        """Load default E-commerce mappings (Expanded)"""
        
        # --- 1. Entities ---
        self.add_entity(SemanticEntity(
            "Customer", "customers", "id", 
            "Individuals who purchase products", 
            ["khách hàng", "người mua", "buyer", "user"]
        ))
        self.add_entity(SemanticEntity(
            "Order", "orders", "id", 
            "Transaction records of purchases", 
            ["đơn hàng", "giao dịch", "purchase"]
        ))
        self.add_entity(SemanticEntity(
            "Product", "products", "id", 
            "Items available for sale", 
            ["sản phẩm", "mặt hàng", "item"]
        ))
        self.add_entity(SemanticEntity(
            "OrderItem", "order_items", "id", 
            "Individual line items in an order", 
            ["chi tiết đơn", "dòng hàng"]
        ))
        
        # --- 2. Relationships (Knowledge Graph) ---
        self.add_relationship(SemanticRelationship(
            "Customer", "Order", "customers.id = orders.customer_id", "one_to_many"
        ))
        self.add_relationship(SemanticRelationship(
            "Order", "OrderItem", "orders.id = order_items.order_id", "one_to_many"
        ))
        self.add_relationship(SemanticRelationship(
            "Product", "OrderItem", "products.id = order_items.product_id", "one_to_many"
        ))
        
        # --- 3. Semantic Metrics ---
        self.add_metric(SemanticMetric(
            "Revenue", "SUM(total_amount)", 
            "Total semantic revenue from orders", 
            "status NOT IN ('cancelled', 'refunded')",
            ["doanh thu", "doanh số", "tổng tiền", "sales"]
        ))
        self.add_metric(SemanticMetric(
            "AOV", "AVG(total_amount)", 
            "Average Order Value",
            "status = 'delivered'",
            ["giá trị đơn trung bình", "average order", "aov"]
        ))
        self.add_metric(SemanticMetric(
            "OrderCount", "COUNT(id)", 
            "Total number of orders",
            None,
            ["số lượng đơn", "tổng đơn", "số đơn hàng"]
        ))
        
        # --- 4. Legacy Mappings (Backward Compat) ---
        self.term_mappings = [
            TermMapping("giá", "price", "products", "Product price"),
            TermMapping("tồn kho", "stock", "products", "Available stock"),
            TermMapping("ngày đặt", "order_date", "orders", "Order date"),
        ]
        
        self.value_mappings = [
            ValueMapping("HN", "Hanoi", "city", "customers"),
            ValueMapping("HCM", "Ho Chi Minh", "city", "customers"),
            ValueMapping("chờ xử lý", "pending", "status", "orders"),
            ValueMapping("đã giao", "delivered", "status", "orders"),
        ]

    def add_entity(self, entity: SemanticEntity):
        self.entities[entity.name] = entity
        self._entity_map[entity.name.lower()] = entity
        for syn in entity.synonyms:
            self._entity_map[syn.lower()] = entity

    def add_metric(self, metric: SemanticMetric):
        self.metrics[metric.name] = metric

    def add_relationship(self, rel: SemanticRelationship):
        self.relationships.append(rel)

    def find_entity(self, term: str) -> Optional[SemanticEntity]:
        return self._entity_map.get(term.lower())

    def find_metric(self, term: str) -> Optional[SemanticMetric]:
        term_lower = term.lower()
        for metric in self.metrics.values():
            if metric.name.lower() == term_lower:
                return metric
            if term_lower in [s.lower() for s in metric.synonyms]:
                return metric
        return None

    def find_path(self, from_entity: str, to_entity: str) -> List[SemanticRelationship]:
        """Simple BFS to find join path between entities"""
        # Note: In production this would be a real graph traversal
        # For now, we implemented direct neighbor lookup or 1-hop
        # This is a simplified implementation
        
        # Direct check
        for rel in self.relationships:
            if (rel.from_entity == from_entity and rel.to_entity == to_entity) or \
               (rel.from_entity == to_entity and rel.to_entity == from_entity):
                   return [rel]
                   
        # 1-hop check (e.g. Customer -> Order -> OrderItem)
        for rel1 in self.relationships:
            mid = None
            if rel1.from_entity == from_entity:
                mid = rel1.to_entity
            elif rel1.to_entity == from_entity:
                mid = rel1.from_entity
            
            if mid:
                for rel2 in self.relationships:
                    if (rel2.from_entity == mid and rel2.to_entity == to_entity) or \
                       (rel2.from_entity == to_entity and rel2.to_entity == mid):
                        if rel2 != rel1:
                            return [rel1, rel2]
        return []

    def get_semantic_context(self, query: str = None) -> str:
        """Generate rich context for LLM, optionally filtered by query relevance"""
        lines = ["## Semantic Knowledge Graph"]
        
        # If query is provided, we can use vector search to find relevant items
        relevant_metrics = list(self.metrics.values())
        relevant_entities = list(self.entities.values())
        
        if query:
            search_results = self.search_definitions(query, k=5)
            if search_results:
                # Filter down to what's relevant + keep core items
                found_metrics = [x['obj'] for x in search_results if x['type'] == 'metric']
                found_entities = [x['obj'] for x in search_results if x['type'] == 'entity']
                
                if found_metrics:
                    relevant_metrics = found_metrics
                # For entities, we usually want to keep most of them or the connected ones
                # For now, let's keep all entities to ensure graph connectivity is visible
                # But we could prioritize found ones.
        
        lines.append("\n### Entities:")
        for e in relevant_entities:
            lines.append(f"- {e.name} (Table: {e.table_name}): {e.description}")
            
        lines.append("\n### Standardized Metrics:")
        for m in relevant_metrics:
            cond = f" WHERE {m.condition}" if m.condition else ""
            lines.append(f"- {m.name}: {m.definition}{cond} ({m.description})")
            
        lines.append("\n### Relationships (Joins):")
        for r in self.relationships:
            lines.append(f"- {r.from_entity} <-> {r.to_entity} ON {r.join_condition}")
            
        lines.append("\n### Value Mappings:")
        for v in self.value_mappings[:5]:
             lines.append(f"- \"{v.alias}\" -> \"{v.actual_value}\" ({v.table}.{v.column})")
             
        return "\n".join(lines)

    # ... keep save/load methods but update them for new structures ...
    def save_to_file(self, filepath: str):
        data = {
            "entities": [asdict(e) for e in self.entities.values()],
            "metrics": [asdict(m) for m in self.metrics.values()],
            "relationships": [asdict(r) for r in self.relationships],
            "term_mappings": [asdict(t) for t in self.term_mappings],
            "value_mappings": [asdict(v) for v in self.value_mappings]
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_from_file(self, filepath: str):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for e_data in data.get("entities", []):
            self.add_entity(SemanticEntity(**e_data))
            
        for m_data in data.get("metrics", []):
            self.add_metric(SemanticMetric(**m_data))
            
        for r_data in data.get("relationships", []):
            self.add_relationship(SemanticRelationship(**r_data))
            
        self.term_mappings = [TermMapping(**m) for m in data.get("term_mappings", [])]
        self.value_mappings = [ValueMapping(**m) for m in data.get("value_mappings", [])]
