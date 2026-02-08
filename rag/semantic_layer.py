"""
Semantic Layer - Maps business terminology to SQL columns/values
Inspired by Uber FINCH's OpenSearch-based semantic layer
"""
from typing import Optional
from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass
class TermMapping:
    """Single term mapping"""
    term: str  # Business term (e.g., "doanh thu", "revenue")
    sql_column: str  # SQL column (e.g., "total_amount")
    table: str  # Table name
    description: str = ""
    synonyms: list[str] = field(default_factory=list)


@dataclass
class ValueMapping:
    """Value alias mapping"""
    alias: str  # User term (e.g., "HN", "Hanoi")
    actual_value: str  # Database value (e.g., "Hanoi")
    column: str  # Column this applies to
    table: str  # Table name


class SemanticLayer:
    """
    Semantic Layer - Business terminology to SQL mapping
    
    Key Features (inspired by FINCH):
    - Map business terms to SQL columns
    - Map value aliases (e.g., "HN" → "Hanoi")
    - Improve WHERE clause accuracy
    - Support multiple languages (Vietnamese/English)
    """
    
    def __init__(self, mappings_file: Optional[str] = None):
        self.term_mappings: list[TermMapping] = []
        self.value_mappings: list[ValueMapping] = []
        
        # Load from file if provided
        if mappings_file and Path(mappings_file).exists():
            self.load_from_file(mappings_file)
        else:
            self._load_default_mappings()
    
    def _load_default_mappings(self):
        """Load default E-commerce mappings"""
        # Term mappings (business terms → SQL columns)
        self.term_mappings = [
            # Revenue / Sales
            TermMapping("doanh thu", "total_amount", "orders", "Total revenue", ["revenue", "sales", "doanh số"]),
            TermMapping("tổng tiền", "total_amount", "orders", "Order total"),
            TermMapping("giá", "price", "products", "Product price", ["price", "giá bán"]),
            
            # Customer
            TermMapping("khách hàng", "name", "customers", "Customer name", ["customer", "KH"]),
            TermMapping("email khách", "email", "customers", "Customer email"),
            TermMapping("thành phố", "city", "customers", "Customer city", ["city", "TP"]),
            
            # Product
            TermMapping("sản phẩm", "name", "products", "Product name", ["product", "SP"]),
            TermMapping("tồn kho", "stock", "products", "Available stock", ["stock", "inventory"]),
            TermMapping("danh mục", "name", "categories", "Category name", ["category"]),
            
            # Order
            TermMapping("đơn hàng", "id", "orders", "Order ID", ["order", "DH"]),
            TermMapping("trạng thái", "status", "orders", "Order status", ["status"]),
            TermMapping("ngày đặt", "order_date", "orders", "Order date", ["order date"]),
            TermMapping("số lượng", "quantity", "order_items", "Item quantity", ["quantity", "SL"]),
            
            # Time
            TermMapping("tháng trước", "order_date >= date('now', '-1 month')", "orders", "Last month filter"),
            TermMapping("năm nay", "order_date >= date('now', 'start of year')", "orders", "This year filter"),
            TermMapping("hôm nay", "order_date = date('now')", "orders", "Today filter"),
        ]
        
        # Value mappings (aliases → actual values)
        self.value_mappings = [
            # Cities
            ValueMapping("HN", "Hanoi", "city", "customers"),
            ValueMapping("HCM", "Ho Chi Minh", "city", "customers"),
            ValueMapping("DN", "Da Nang", "city", "customers"),
            ValueMapping("Saigon", "Ho Chi Minh", "city", "customers"),
            
            # Order statuses
            ValueMapping("chờ xử lý", "pending", "status", "orders"),
            ValueMapping("đã xác nhận", "confirmed", "status", "orders"),
            ValueMapping("đang giao", "shipped", "status", "orders"),
            ValueMapping("đã giao", "delivered", "status", "orders"),
            ValueMapping("đã hủy", "cancelled", "status", "orders"),
        ]
    
    def add_term_mapping(self, term: str, sql_column: str, table: str, 
                         description: str = "", synonyms: list[str] = None):
        """Add a term mapping"""
        self.term_mappings.append(TermMapping(
            term=term.lower(),
            sql_column=sql_column,
            table=table,
            description=description,
            synonyms=[s.lower() for s in (synonyms or [])]
        ))
    
    def add_value_mapping(self, alias: str, actual_value: str, column: str, table: str):
        """Add a value mapping"""
        self.value_mappings.append(ValueMapping(
            alias=alias.lower(),
            actual_value=actual_value,
            column=column,
            table=table
        ))
    
    def find_term_mapping(self, term: str) -> Optional[TermMapping]:
        """Find mapping for a business term"""
        term_lower = term.lower()
        for mapping in self.term_mappings:
            if mapping.term == term_lower:
                return mapping
            if term_lower in mapping.synonyms:
                return mapping
        return None
    
    def find_value_mapping(self, alias: str) -> Optional[ValueMapping]:
        """Find mapping for a value alias"""
        alias_lower = alias.lower()
        for mapping in self.value_mappings:
            if mapping.alias == alias_lower:
                return mapping
        return None
    
    def get_mappings_description(self) -> str:
        """Generate description of mappings for LLM prompt"""
        lines = ["## Semantic Mappings\n"]
        lines.append("### Business Terms → SQL Columns:")
        
        for m in self.term_mappings[:15]:  # Limit to avoid token bloat
            synonyms = f" (also: {', '.join(m.synonyms)})" if m.synonyms else ""
            lines.append(f"  - \"{m.term}\"{synonyms} → {m.table}.{m.sql_column}")
        
        lines.append("\n### Value Aliases:")
        for m in self.value_mappings[:10]:
            lines.append(f"  - \"{m.alias}\" → \"{m.actual_value}\" (for {m.table}.{m.column})")
        
        return "\n".join(lines)
    
    def translate_query(self, question: str) -> str:
        """Translate business terms in question to SQL-friendly terms"""
        translated = question
        
        # Replace value aliases
        for mapping in self.value_mappings:
            if mapping.alias in question.lower():
                translated = translated.replace(mapping.alias, mapping.actual_value)
        
        return translated
    
    def save_to_file(self, filepath: str):
        """Save mappings to JSON file"""
        data = {
            "term_mappings": [
                {
                    "term": m.term,
                    "sql_column": m.sql_column,
                    "table": m.table,
                    "description": m.description,
                    "synonyms": m.synonyms
                }
                for m in self.term_mappings
            ],
            "value_mappings": [
                {
                    "alias": m.alias,
                    "actual_value": m.actual_value,
                    "column": m.column,
                    "table": m.table
                }
                for m in self.value_mappings
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_from_file(self, filepath: str):
        """Load mappings from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.term_mappings = [
            TermMapping(**m) for m in data.get("term_mappings", [])
        ]
        self.value_mappings = [
            ValueMapping(**m) for m in data.get("value_mappings", [])
        ]
