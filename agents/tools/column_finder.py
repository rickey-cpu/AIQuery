"""
Column Finder Tool - Search columns by semantic meaning
Inspired by FINCH's self-querying capability
"""
from typing import Optional
from dataclasses import dataclass, field
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class ColumnMatch(BaseModel):
    """A matched column result"""
    table: str = Field(description="Table name")
    column: str = Field(description="Column name")
    data_type: str = Field(description="Column data type")
    description: str = Field(default="", description="Column description")
    score: float = Field(default=1.0, description="Match confidence score")


class ColumnFinderInput(BaseModel):
    """Input for Column Finder Tool"""
    search_term: str = Field(description="Business term to search for (e.g., 'revenue', 'GBs', 'doanh thu')")


class ColumnFinderTool(BaseTool):
    """
    Column Finder Tool - Tìm columns theo semantic meaning
    
    Như trong FINCH diagram:
    - Input: business term (e.g., "GBs" for Gross Bookings)
    - Output: matching columns with table, type, description
    
    Builds Agent Context: table + column info
    """
    
    name: str = "column_finder"
    description: str = """Find database columns that match a business term or concept.
Use this tool when you need to identify which table and column to use for a metric or field.
Input should be a business term like 'revenue', 'customer', 'order date', etc."""
    args_schema: type[BaseModel] = ColumnFinderInput
    
    # Column index for semantic search
    _column_index: dict = {}
    
    def __init__(self, schema_manager=None, semantic_layer=None, **kwargs):
        super().__init__(**kwargs)
        self.schema_manager = schema_manager
        self.semantic_layer = semantic_layer
        self._build_index()
    
    def _build_index(self):
        """Build searchable index from schema and semantic layer"""
        self._column_index = {}
        
        # Default E-commerce column mappings
        default_mappings = {
            # Revenue/Money
            "revenue": ("orders", "total_amount", "REAL", "Total order revenue"),
            "doanh thu": ("orders", "total_amount", "REAL", "Total order revenue"),
            "total": ("orders", "total_amount", "REAL", "Order total amount"),
            "amount": ("orders", "total_amount", "REAL", "Order amount"),
            "price": ("products", "price", "REAL", "Product price"),
            "giá": ("products", "price", "REAL", "Product price"),
            
            # Customers
            "customer": ("customers", "name", "TEXT", "Customer name"),
            "khách hàng": ("customers", "name", "TEXT", "Customer name"),
            "email": ("customers", "email", "TEXT", "Customer email"),
            "city": ("customers", "city", "TEXT", "Customer city"),
            "thành phố": ("customers", "city", "TEXT", "Customer city"),
            
            # Products
            "product": ("products", "name", "TEXT", "Product name"),
            "sản phẩm": ("products", "name", "TEXT", "Product name"),
            "stock": ("products", "stock", "INTEGER", "Available stock"),
            "tồn kho": ("products", "stock", "INTEGER", "Available stock"),
            "category": ("categories", "name", "TEXT", "Category name"),
            "danh mục": ("categories", "name", "TEXT", "Category name"),
            
            # Orders
            "order": ("orders", "id", "INTEGER", "Order ID"),
            "đơn hàng": ("orders", "id", "INTEGER", "Order ID"),
            "status": ("orders", "status", "TEXT", "Order status"),
            "trạng thái": ("orders", "status", "TEXT", "Order status"),
            "order date": ("orders", "order_date", "DATETIME", "Order placement date"),
            "ngày đặt": ("orders", "order_date", "DATETIME", "Order date"),
            "date": ("orders", "order_date", "DATETIME", "Order date"),
            
            # Order Items
            "quantity": ("order_items", "quantity", "INTEGER", "Item quantity"),
            "số lượng": ("order_items", "quantity", "INTEGER", "Quantity"),
            
            # Aggregations hints
            "count": ("*", "COUNT(*)", "INTEGER", "Count of records"),
            "sum": ("*", "SUM()", "REAL", "Sum aggregation"),
            "average": ("*", "AVG()", "REAL", "Average aggregation"),
            "total count": ("*", "COUNT(*)", "INTEGER", "Total count"),
        }
        
        self._column_index = default_mappings
        
        # Add from semantic layer if available
        if self.semantic_layer:
            for mapping in self.semantic_layer.term_mappings:
                self._column_index[mapping.term] = (
                    mapping.table,
                    mapping.sql_column,
                    "UNKNOWN",
                    mapping.description
                )
                for syn in mapping.synonyms:
                    self._column_index[syn] = (
                        mapping.table,
                        mapping.sql_column,
                        "UNKNOWN",
                        mapping.description
                    )
    
    def _run(self, search_term: str) -> list[dict]:
        """Find columns matching the search term"""
        search_lower = search_term.lower().strip()
        results = []
        
        # Direct match
        if search_lower in self._column_index:
            table, column, dtype, desc = self._column_index[search_lower]
            results.append({
                "table": table,
                "column": column,
                "data_type": dtype,
                "description": desc,
                "score": 1.0
            })
        
        # Partial match
        for term, (table, column, dtype, desc) in self._column_index.items():
            if term != search_lower:
                if search_lower in term or term in search_lower:
                    results.append({
                        "table": table,
                        "column": column,
                        "data_type": dtype,
                        "description": desc,
                        "score": 0.7
                    })
        
        # Fuzzy matching using word overlap
        search_words = set(search_lower.split())
        for term, (table, column, dtype, desc) in self._column_index.items():
            term_words = set(term.split())
            overlap = search_words & term_words
            if overlap and term != search_lower:
                score = len(overlap) / max(len(search_words), len(term_words))
                if score > 0.3:
                    results.append({
                        "table": table,
                        "column": column,
                        "data_type": dtype,
                        "description": desc,
                        "score": score * 0.5
                    })
        
        # Deduplicate and sort by score
        seen = set()
        unique_results = []
        for r in sorted(results, key=lambda x: x["score"], reverse=True):
            key = (r["table"], r["column"])
            if key not in seen:
                seen.add(key)
                unique_results.append(r)
        
        return unique_results[:5]  # Top 5 matches
    
    async def _arun(self, search_term: str) -> list[dict]:
        """Async version"""
        return self._run(search_term)
