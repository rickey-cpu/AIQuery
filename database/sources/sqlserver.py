"""
SQL Server Connector - Async SQL Server/MSSQL connection
"""
from typing import Optional, Any
import asyncio


class SQLServerConnector:
    """
    SQL Server / MSSQL Connector
    
    Dependencies:
        pip install aioodbc pyodbc
    
    Usage:
        connector = SQLServerConnector(
            host="localhost",
            port=1433,
            database="mydb",
            user="sa",
            password="password"
        )
        await connector.connect()
        result = await connector.execute("SELECT TOP 10 * FROM users")
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 1433,
        database: str = "",
        user: str = "sa",
        password: str = "",
        driver: str = "ODBC Driver 17 for SQL Server"
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.driver = driver
        self._pool = None
    
    def _get_connection_string(self) -> str:
        """Build ODBC connection string"""
        return (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.host},{self.port};"
            f"DATABASE={self.database};"
            f"UID={self.user};"
            f"PWD={self.password};"
            "TrustServerCertificate=yes;"
        )
    
    async def connect(self):
        """Create connection pool"""
        try:
            import aioodbc
            self._pool = await aioodbc.create_pool(
                dsn=self._get_connection_string(),
                minsize=1,
                maxsize=5
            )
        except ImportError:
            raise ImportError("aioodbc is required. Install with: pip install aioodbc pyodbc")
    
    async def disconnect(self):
        """Close connection pool"""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
    
    async def execute(self, sql: str, params: tuple = None) -> dict:
        """Execute query and return results"""
        if not self._pool:
            await self.connect()
        
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                if params:
                    await cursor.execute(sql, params)
                else:
                    await cursor.execute(sql)
                
                # Get column names
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                
                # Fetch all rows
                rows = await cursor.fetchall()
                
                return {
                    "columns": columns,
                    "rows": [list(row) for row in rows],
                    "row_count": len(rows)
                }
    
    async def get_tables(self) -> list[str]:
        """Get list of tables"""
        sql = """
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """
        result = await self.execute(sql)
        return [row[0] for row in result["rows"]]
    
    async def get_schema(self, table: str) -> list[dict]:
        """Get table schema"""
        sql = """
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """
        result = await self.execute(sql, (table,))
        return [
            {
                "column": row[0],
                "type": row[1],
                "nullable": row[2] == "YES",
                "default": row[3]
            }
            for row in result["rows"]
        ]
    
    async def test_connection(self) -> bool:
        """Test database connection"""
        try:
            await self.execute("SELECT 1")
            return True
        except Exception:
            return False
