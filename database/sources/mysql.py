"""
MySQL Connector - Async MySQL/MariaDB connection
"""
from typing import Optional, Any
import asyncio


class MySQLConnector:
    """
    MySQL/MariaDB Connector
    
    Dependencies:
        pip install aiomysql
    
    Usage:
        connector = MySQLConnector(
            host="localhost",
            port=3306,
            database="mydb",
            user="root",
            password="password"
        )
        await connector.connect()
        result = await connector.execute("SELECT * FROM users LIMIT 10")
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 3306,
        database: str = "",
        user: str = "root",
        password: str = "",
        pool_size: int = 5
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.pool_size = pool_size
        self._pool = None
    
    async def connect(self):
        """Create connection pool"""
        try:
            import aiomysql
            self._pool = await aiomysql.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.database,
                minsize=1,
                maxsize=self.pool_size,
                autocommit=True
            )
        except ImportError:
            raise ImportError("aiomysql is required. Install with: pip install aiomysql")
    
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
                await cursor.execute(sql, params or ())
                
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
        result = await self.execute("SHOW TABLES")
        return [row[0] for row in result["rows"]]
    
    async def get_schema(self, table: str) -> list[dict]:
        """Get table schema"""
        result = await self.execute(f"DESCRIBE `{table}`")
        return [
            {
                "column": row[0],
                "type": row[1],
                "nullable": row[2] == "YES",
                "key": row[3],
                "default": row[4]
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
