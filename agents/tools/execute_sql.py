"""
Execute SQL Tool - Safe SQL execution with result formatting
Inspired by FINCH's execute SQL capability
"""
from typing import Any, Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import re


class ExecuteSQLInput(BaseModel):
    """Input for Execute SQL Tool"""
    sql: str = Field(description="SQL query to execute")
    limit: int = Field(default=100, description="Maximum rows to return")


class ExecuteSQLTool(BaseTool):
    """
    Execute SQL Tool - Safe SQL execution with validation
    
    Features:
    - Query validation before execution
    - Result formatting
    - Row limiting for safety
    - Export link generation (future: Google Sheets)
    """
    
    name: str = "execute_sql"
    description: str = """Execute a SQL query and return the results.
Only SELECT queries are allowed. Results are automatically limited for safety.
Returns columns, rows, and row count."""
    args_schema: type[BaseModel] = ExecuteSQLInput
    
    # Blocked patterns
    BLOCKED_PATTERNS = [
        r'\bDROP\b', r'\bDELETE\b', r'\bTRUNCATE\b',
        r'\bALTER\b', r'\bCREATE\b', r'\bINSERT\b',
        r'\bUPDATE\b', r'\bGRANT\b', r'\bREVOKE\b',
    ]
    
    def __init__(self, db_connector=None, **kwargs):
        super().__init__(**kwargs)
        self.db_connector = db_connector
        self._blocked = [re.compile(p, re.IGNORECASE) for p in self.BLOCKED_PATTERNS]
    
    def _validate_sql(self, sql: str) -> tuple[bool, str]:
        """Validate SQL before execution"""
        sql_clean = sql.strip()
        
        # Must be SELECT
        if not sql_clean.upper().startswith('SELECT'):
            return False, "Only SELECT queries are allowed"
        
        # Check blocked patterns
        for pattern in self._blocked:
            if pattern.search(sql_clean):
                return False, f"Blocked operation detected"
        
        return True, ""
    
    def _clean_sql(self, sql: str, limit: int) -> str:
        """Clean and add limit to SQL"""
        sql_clean = sql.strip().rstrip(';')
        
        # Add LIMIT if not present
        if not re.search(r'\bLIMIT\b', sql_clean, re.IGNORECASE):
            # Don't add limit to aggregate queries without GROUP BY that return single row
            has_agg = re.search(r'\b(COUNT|SUM|AVG|MAX|MIN)\s*\(', sql_clean, re.IGNORECASE)
            has_group = re.search(r'\bGROUP\s+BY\b', sql_clean, re.IGNORECASE)
            
            if not has_agg or has_group:
                sql_clean += f' LIMIT {limit}'
        
        return sql_clean
    
    def _run(self, sql: str, limit: int = 100) -> dict:
        """Execute SQL query"""
        # Validate
        is_valid, error = self._validate_sql(sql)
        if not is_valid:
            return {
                "success": False,
                "error": error,
                "sql": sql
            }
        
        # Clean SQL
        clean_sql = self._clean_sql(sql, limit)
        
        # Execute
        if self.db_connector:
            import asyncio
            try:
                # Try to get running loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in an async context, create a future
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        future = pool.submit(
                            asyncio.run,
                            self.db_connector.execute(clean_sql)
                        )
                        result = future.result()
                else:
                    result = asyncio.run(self.db_connector.execute(clean_sql))
                
                return {
                    "success": True,
                    "sql": clean_sql,
                    "columns": result.get("columns", []),
                    "rows": result.get("rows", []),
                    "row_count": result.get("row_count", 0)
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "sql": clean_sql
                }
        else:
            # Demo mode - return sample result
            return {
                "success": True,
                "sql": clean_sql,
                "columns": ["id", "name", "value"],
                "rows": [
                    [1, "Sample A", 100],
                    [2, "Sample B", 200],
                    [3, "Sample C", 300]
                ],
                "row_count": 3,
                "note": "Demo mode - no database connected"
            }
    
    async def _arun(self, sql: str, limit: int = 100) -> dict:
        """Async execute SQL query"""
        # Validate
        is_valid, error = self._validate_sql(sql)
        if not is_valid:
            return {
                "success": False,
                "error": error,
                "sql": sql
            }
        
        # Clean SQL
        clean_sql = self._clean_sql(sql, limit)
        
        # Execute
        if self.db_connector:
            try:
                result = await self.db_connector.execute(clean_sql)
                return {
                    "success": True,
                    "sql": clean_sql,
                    "columns": result.get("columns", []),
                    "rows": result.get("rows", []),
                    "row_count": result.get("row_count", 0)
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "sql": clean_sql
                }
        else:
            return self._run(sql, limit)
    
    def format_as_table(self, result: dict) -> str:
        """Format result as ASCII table for display"""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"
        
        columns = result.get("columns", [])
        rows = result.get("rows", [])
        
        if not columns:
            return "No results"
        
        # Calculate column widths
        widths = [len(str(col)) for col in columns]
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(str(cell)))
        
        # Build table
        lines = []
        header = " | ".join(str(col).ljust(widths[i]) for i, col in enumerate(columns))
        separator = "-+-".join("-" * w for w in widths)
        
        lines.append(header)
        lines.append(separator)
        
        for row in rows:
            line = " | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row))
            lines.append(line)
        
        lines.append(f"\n({result.get('row_count', 0)} rows)")
        
        return "\n".join(lines)
