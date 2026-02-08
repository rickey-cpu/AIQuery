"""
Value Finder Tool - Find actual database values for aliases
Inspired by FINCH's value resolution capability
"""
from typing import Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr


class ValueFinderInput(BaseModel):
    """Input for Value Finder Tool"""
    alias: str = Field(description="Alias or abbreviation to resolve (e.g., 'US&C', 'HN', 'APAC')")
    column: str = Field(default="", description="Optional: column context for better matching")


class ValueFinderTool(BaseTool):
    """
    Value Finder Tool - Resolve value aliases to actual database values
    
    Như trong FINCH diagram:
    - Input: "US&C" (US and Canada region)
    - Output: value = "US", "CA" for country columns
    
    Builds Agent Context: column + value info for WHERE clauses
    """
    
    name: str = "value_finder"
    description: str = """Find the actual database values for a given alias or abbreviation.
Use this tool when the user mentions abbreviated terms like 'HN' for 'Hanoi', 
'US&C' for 'US and Canada', or status abbreviations.
Returns the actual values to use in SQL WHERE clauses."""
    args_schema: type[BaseModel] = ValueFinderInput
    
    # Internal state
    _value_index: dict = PrivateAttr(default_factory=dict)
    _semantic_layer: Optional[object] = PrivateAttr(default=None)
    
    def __init__(self, semantic_layer=None, **kwargs):
        super().__init__(**kwargs)
        self._semantic_layer = semantic_layer
        self._build_index()
    
    def _build_index(self):
        """Build value mappings index"""
        # Default value mappings
        self._value_index = {
            # Geographic
            "hn": {"column": "city", "values": ["Hanoi"], "description": "Hanoi city"},
            "hanoi": {"column": "city", "values": ["Hanoi"], "description": "Hanoi city"},
            "hcm": {"column": "city", "values": ["Ho Chi Minh"], "description": "Ho Chi Minh City"},
            "saigon": {"column": "city", "values": ["Ho Chi Minh"], "description": "Ho Chi Minh City"},
            "dn": {"column": "city", "values": ["Da Nang"], "description": "Da Nang city"},
            "us&c": {"column": "region", "values": ["US", "CA"], "description": "US and Canada region"},
            "apac": {"column": "region", "values": ["APAC"], "description": "Asia Pacific region"},
            "emea": {"column": "region", "values": ["EMEA"], "description": "Europe, Middle East, Africa"},
            
            # Order statuses - Vietnamese
            "chờ xử lý": {"column": "status", "values": ["pending"], "description": "Pending status"},
            "đang xử lý": {"column": "status", "values": ["pending"], "description": "Processing"},
            "đã xác nhận": {"column": "status", "values": ["confirmed"], "description": "Confirmed status"},
            "đang giao": {"column": "status", "values": ["shipped"], "description": "Being shipped"},
            "đã giao": {"column": "status", "values": ["delivered"], "description": "Delivered"},
            "đã hủy": {"column": "status", "values": ["cancelled"], "description": "Cancelled"},
            "hoàn thành": {"column": "status", "values": ["delivered"], "description": "Completed"},
            
            # Order statuses - English shortcuts
            "pending": {"column": "status", "values": ["pending"], "description": "Pending"},
            "confirmed": {"column": "status", "values": ["confirmed"], "description": "Confirmed"},
            "shipped": {"column": "status", "values": ["shipped"], "description": "Shipped"},
            "delivered": {"column": "status", "values": ["delivered"], "description": "Delivered"},
            "cancelled": {"column": "status", "values": ["cancelled"], "description": "Cancelled"},
            
            # Time periods
            "last month": {"column": "date", "values": ["date('now', '-1 month')"], "description": "Last month", "is_expression": True},
            "tháng trước": {"column": "date", "values": ["date('now', '-1 month')"], "description": "Last month", "is_expression": True},
            "this month": {"column": "date", "values": ["date('now', 'start of month')"], "description": "This month", "is_expression": True},
            "tháng này": {"column": "date", "values": ["date('now', 'start of month')"], "description": "This month", "is_expression": True},
            "this year": {"column": "date", "values": ["date('now', 'start of year')"], "description": "This year", "is_expression": True},
            "năm nay": {"column": "date", "values": ["date('now', 'start of year')"], "description": "This year", "is_expression": True},
            "last year": {"column": "date", "values": ["date('now', '-1 year')"], "description": "Last year", "is_expression": True},
            "năm trước": {"column": "date", "values": ["date('now', '-1 year')"], "description": "Last year", "is_expression": True},
            "today": {"column": "date", "values": ["date('now')"], "description": "Today", "is_expression": True},
            "hôm nay": {"column": "date", "values": ["date('now')"], "description": "Today", "is_expression": True},
            "yesterday": {"column": "date", "values": ["date('now', '-1 day')"], "description": "Yesterday", "is_expression": True},
            "hôm qua": {"column": "date", "values": ["date('now', '-1 day')"], "description": "Yesterday", "is_expression": True},
            
            # Quarter shortcuts
            "q1": {"column": "date", "values": ["01", "02", "03"], "description": "Q1 (Jan-Mar)", "type": "months"},
            "q2": {"column": "date", "values": ["04", "05", "06"], "description": "Q2 (Apr-Jun)", "type": "months"},
            "q3": {"column": "date", "values": ["07", "08", "09"], "description": "Q3 (Jul-Sep)", "type": "months"},
            "q4": {"column": "date", "values": ["10", "11", "12"], "description": "Q4 (Oct-Dec)", "type": "months"},
            "last quarter": {"column": "date", "values": ["date('now', '-3 months')"], "description": "Last quarter", "is_expression": True},
            "quý trước": {"column": "date", "values": ["date('now', '-3 months')"], "description": "Last quarter", "is_expression": True},
            
            # Categories
            "electronics": {"column": "category", "values": ["Electronics"], "description": "Electronics category"},
            "điện tử": {"column": "category", "values": ["Electronics"], "description": "Electronics"},
            "clothing": {"column": "category", "values": ["Clothing"], "description": "Clothing category"},
            "quần áo": {"column": "category", "values": ["Clothing"], "description": "Clothing"},
            "books": {"column": "category", "values": ["Books"], "description": "Books category"},
            "sách": {"column": "category", "values": ["Books"], "description": "Books"},
        }
        
        # Add from semantic layer if available
        if self._semantic_layer:
            for mapping in self._semantic_layer.value_mappings:
                self._value_index[mapping.alias.lower()] = {
                    "column": mapping.column,
                    "values": [mapping.actual_value],
                    "description": f"Maps to {mapping.actual_value}"
                }
    
    def _run(self, alias: str, column: str = "") -> dict:
        """Find actual values for an alias"""
        alias_lower = alias.lower().strip()
        
        # Direct match
        if alias_lower in self._value_index:
            result = self._value_index[alias_lower].copy()
            result["alias"] = alias
            result["found"] = True
            return result
        
        # Partial match
        for key, value in self._value_index.items():
            if alias_lower in key or key in alias_lower:
                result = value.copy()
                result["alias"] = alias
                result["found"] = True
                result["partial_match"] = True
                return result
        
        # Not found - return the original value as-is
        return {
            "alias": alias,
            "column": column,
            "values": [alias],  # Use original value
            "description": "No mapping found, using original value",
            "found": False
        }
    
    async def _arun(self, alias: str, column: str = "") -> dict:
        """Async version"""
        return self._run(alias, column)
