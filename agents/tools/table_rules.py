"""
Table Rules Tool - Get table-specific rules and constraints
Inspired by FINCH's table rules retrieval
"""
from typing import Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class TableRulesInput(BaseModel):
    """Input for Table Rules Tool"""
    table_name: str = Field(description="Table name to get rules for")


class TableRulesTool(BaseTool):
    """
    Get Table Rules Tool - Retrieve table-specific rules and constraints
    
    Như trong FINCH diagram:
    - Required columns (e.g., accounting_date)
    - Default values (e.g., rate_type = 'USD')
    - Example queries for few-shot
    - Business logic constraints
    
    Builds Agent Context: rules info for correct SQL generation
    """
    
    name: str = "get_table_rules"
    description: str = """Get rules, constraints, and example queries for a specific table.
Use this tool before writing SQL to understand required columns, default values, 
and proper query patterns for the table."""
    args_schema: type[BaseModel] = TableRulesInput
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rules = self._build_rules()
    
    def _build_rules(self) -> dict:
        """Build table rules index"""
        return {
            "customers": {
                "table": "customers",
                "description": "Customer information table",
                "required_columns": [],
                "default_filters": {},
                "common_columns": ["id", "name", "email", "city"],
                "join_hints": [
                    {"target": "orders", "on": "customers.id = orders.customer_id"}
                ],
                "example_queries": [
                    {
                        "question": "All customers from Hanoi",
                        "sql": "SELECT * FROM customers WHERE city = 'Hanoi'"
                    },
                    {
                        "question": "Customer count by city",
                        "sql": "SELECT city, COUNT(*) as count FROM customers GROUP BY city ORDER BY count DESC"
                    }
                ],
                "notes": ["City values: Hanoi, Ho Chi Minh, Da Nang, Can Tho, Hai Phong"]
            },
            
            "products": {
                "table": "products",
                "description": "Product catalog table",
                "required_columns": [],
                "default_filters": {"stock": "> 0"},
                "common_columns": ["id", "name", "price", "category_id", "stock"],
                "join_hints": [
                    {"target": "categories", "on": "products.category_id = categories.id"},
                    {"target": "order_items", "on": "products.id = order_items.product_id"}
                ],
                "example_queries": [
                    {
                        "question": "Products under $50",
                        "sql": "SELECT * FROM products WHERE price < 50"
                    },
                    {
                        "question": "Products by category",
                        "sql": "SELECT c.name as category, COUNT(p.id) as count FROM categories c LEFT JOIN products p ON c.id = p.category_id GROUP BY c.id"
                    }
                ],
                "notes": ["Price is in USD", "Use stock > 0 for available products only"]
            },
            
            "orders": {
                "table": "orders",
                "description": "Customer orders table",
                "required_columns": ["customer_id"],
                "default_filters": {},
                "common_columns": ["id", "customer_id", "order_date", "status", "total_amount"],
                "join_hints": [
                    {"target": "customers", "on": "orders.customer_id = customers.id"},
                    {"target": "order_items", "on": "orders.id = order_items.order_id"}
                ],
                "aggregation_hints": {
                    "revenue": "SUM(total_amount)",
                    "order_count": "COUNT(*)",
                    "avg_order": "AVG(total_amount)"
                },
                "example_queries": [
                    {
                        "question": "Total revenue",
                        "sql": "SELECT SUM(total_amount) as total_revenue FROM orders"
                    },
                    {
                        "question": "Revenue by month",
                        "sql": "SELECT strftime('%Y-%m', order_date) as month, SUM(total_amount) as revenue FROM orders GROUP BY month ORDER BY month"
                    },
                    {
                        "question": "Orders by status",
                        "sql": "SELECT status, COUNT(*) as count FROM orders GROUP BY status"
                    }
                ],
                "notes": [
                    "Status values: pending, confirmed, shipped, delivered, cancelled",
                    "total_amount is in USD",
                    "Use strftime('%Y-%m', order_date) for monthly grouping"
                ]
            },
            
            "order_items": {
                "table": "order_items",
                "description": "Line items in each order",
                "required_columns": ["order_id", "product_id"],
                "default_filters": {},
                "common_columns": ["id", "order_id", "product_id", "quantity", "unit_price"],
                "join_hints": [
                    {"target": "orders", "on": "order_items.order_id = orders.id"},
                    {"target": "products", "on": "order_items.product_id = products.id"}
                ],
                "aggregation_hints": {
                    "total_quantity": "SUM(quantity)",
                    "line_total": "SUM(quantity * unit_price)"
                },
                "example_queries": [
                    {
                        "question": "Top selling products",
                        "sql": "SELECT p.name, SUM(oi.quantity) as total_sold FROM products p JOIN order_items oi ON p.id = oi.product_id GROUP BY p.id ORDER BY total_sold DESC LIMIT 10"
                    }
                ],
                "notes": ["unit_price captures price at time of order"]
            },
            
            "categories": {
                "table": "categories",
                "description": "Product categories",
                "required_columns": [],
                "default_filters": {},
                "common_columns": ["id", "name", "parent_id"],
                "join_hints": [
                    {"target": "products", "on": "categories.id = products.category_id"}
                ],
                "example_queries": [
                    {
                        "question": "All categories",
                        "sql": "SELECT * FROM categories"
                    }
                ],
                "notes": ["Categories: Electronics, Clothing, Books, Home & Garden, Sports"]
            }
        }
    
    def _run(self, table_name: str) -> dict:
        """Get rules for a table"""
        table_lower = table_name.lower().strip()
        
        if table_lower in self._rules:
            return self._rules[table_lower]
        
        # Try partial match
        for name, rules in self._rules.items():
            if table_lower in name or name in table_lower:
                return rules
        
        # Return generic rules
        return {
            "table": table_name,
            "description": "Table not found in rules database",
            "required_columns": [],
            "default_filters": {},
            "common_columns": [],
            "join_hints": [],
            "example_queries": [],
            "notes": ["No specific rules available for this table"]
        }
    
    async def _arun(self, table_name: str) -> dict:
        """Async version"""
        return self._run(table_name)
    
    def get_all_tables(self) -> list[str]:
        """Get list of all tables with rules"""
        return list(self._rules.keys())
