"""
Schema Manager - Manages database schema metadata for SQL generation
"""
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class ColumnInfo:
    """Column metadata"""
    name: str
    data_type: str
    nullable: bool = True
    primary_key: bool = False
    foreign_key: Optional[str] = None
    description: str = ""


@dataclass 
class TableInfo:
    """Table metadata"""
    name: str
    columns: list[ColumnInfo] = field(default_factory=list)
    description: str = ""
    row_count: int = 0


class SchemaManager:
    """
    Schema Manager - Provides schema context for SQL generation
    
    Features:
    - Auto-extract schema from database
    - Generate human-readable schema descriptions
    - Track table relationships
    """
    
    def __init__(self, db_connector=None):
        self.db_connector = db_connector
        self.tables: dict[str, TableInfo] = {}
        
        # Load default E-commerce schema
        self._load_default_schema()
    
    def _load_default_schema(self):
        """Load default E-commerce schema"""
        # Customers table
        self.tables["customers"] = TableInfo(
            name="customers",
            description="Customer information",
            columns=[
                ColumnInfo("id", "INTEGER", primary_key=True),
                ColumnInfo("name", "TEXT", description="Customer full name"),
                ColumnInfo("email", "TEXT", description="Customer email address"),
                ColumnInfo("phone", "TEXT", nullable=True),
                ColumnInfo("city", "TEXT", description="Customer city"),
                ColumnInfo("created_at", "DATETIME", description="Registration date"),
            ]
        )
        
        # Products table
        self.tables["products"] = TableInfo(
            name="products",
            description="Product catalog",
            columns=[
                ColumnInfo("id", "INTEGER", primary_key=True),
                ColumnInfo("name", "TEXT", description="Product name"),
                ColumnInfo("description", "TEXT", nullable=True),
                ColumnInfo("price", "REAL", description="Product price in USD"),
                ColumnInfo("category_id", "INTEGER", foreign_key="categories.id"),
                ColumnInfo("stock", "INTEGER", description="Available stock"),
                ColumnInfo("created_at", "DATETIME"),
            ]
        )
        
        # Categories table
        self.tables["categories"] = TableInfo(
            name="categories",
            description="Product categories",
            columns=[
                ColumnInfo("id", "INTEGER", primary_key=True),
                ColumnInfo("name", "TEXT", description="Category name"),
                ColumnInfo("parent_id", "INTEGER", nullable=True, foreign_key="categories.id"),
            ]
        )
        
        # Orders table
        self.tables["orders"] = TableInfo(
            name="orders",
            description="Customer orders",
            columns=[
                ColumnInfo("id", "INTEGER", primary_key=True),
                ColumnInfo("customer_id", "INTEGER", foreign_key="customers.id"),
                ColumnInfo("order_date", "DATETIME", description="Order placement date"),
                ColumnInfo("status", "TEXT", description="Order status: pending, confirmed, shipped, delivered, cancelled"),
                ColumnInfo("total_amount", "REAL", description="Total order value in USD"),
                ColumnInfo("shipping_address", "TEXT"),
            ]
        )
        
        # Order Items table
        self.tables["order_items"] = TableInfo(
            name="order_items",
            description="Items in each order",
            columns=[
                ColumnInfo("id", "INTEGER", primary_key=True),
                ColumnInfo("order_id", "INTEGER", foreign_key="orders.id"),
                ColumnInfo("product_id", "INTEGER", foreign_key="products.id"),
                ColumnInfo("quantity", "INTEGER"),
                ColumnInfo("unit_price", "REAL", description="Price at time of order"),
            ]
        )
    
    async def refresh_from_database(self):
        """Refresh schema from actual database"""
        if not self.db_connector:
            return
        
        # Query SQLite schema
        tables_query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        tables = await self.db_connector.execute(tables_query)
        
        for table_row in tables.get("rows", []):
            table_name = table_row[0]
            columns_query = f"PRAGMA table_info({table_name})"
            columns = await self.db_connector.execute(columns_query)
            
            column_infos = []
            for col in columns.get("rows", []):
                column_infos.append(ColumnInfo(
                    name=col[1],
                    data_type=col[2],
                    nullable=col[3] == 0,
                    primary_key=col[5] == 1
                ))
            
            self.tables[table_name] = TableInfo(
                name=table_name,
                columns=column_infos
            )
    
    def get_schema_description(self) -> str:
        """Generate human-readable schema description for LLM"""
        lines = ["## Database Schema\n"]
        
        for table_name, table in self.tables.items():
            lines.append(f"### Table: {table_name}")
            if table.description:
                lines.append(f"Description: {table.description}")
            lines.append("Columns:")
            
            for col in table.columns:
                pk = " (PK)" if col.primary_key else ""
                fk = f" -> {col.foreign_key}" if col.foreign_key else ""
                desc = f" - {col.description}" if col.description else ""
                lines.append(f"  - {col.name}: {col.data_type}{pk}{fk}{desc}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def get_table_names(self) -> list[str]:
        """Get list of all table names"""
        return list(self.tables.keys())
    
    def get_table_info(self, table_name: str) -> Optional[TableInfo]:
        """Get info for specific table"""
        return self.tables.get(table_name)
    
    def get_column_names(self, table_name: str) -> list[str]:
        """Get column names for a table"""
        table = self.tables.get(table_name)
        if table:
            return [col.name for col in table.columns]
        return []
