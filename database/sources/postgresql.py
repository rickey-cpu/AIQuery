"""
PostgreSQL Connector - Async PostgreSQL connection
"""
from typing import Optional, Any


class PostgreSQLConnector:
    """
    PostgreSQL Connector
    
    Dependencies:
        pip install asyncpg
    
    Usage:
        connector = PostgreSQLConnector(
            host="localhost",
            port=5432,
            database="mydb",
            user="postgres",
            password="password"
        )
        await connector.connect()
        result = await connector.execute("SELECT * FROM users LIMIT 10")
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "",
        user: str = "postgres",
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
            import asyncpg
            self._pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                min_size=1,
                max_size=self.pool_size
            )
        except ImportError:
            raise ImportError("asyncpg is required. Install with: pip install asyncpg")
    
    async def disconnect(self):
        """Close connection pool"""
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    async def execute(self, sql: str, params: tuple = None) -> dict:
        """Execute query and return results"""
        if not self._pool:
            await self.connect()
        
        async with self._pool.acquire() as conn:
            # Execute query
            if params:
                rows = await conn.fetch(sql, *params)
            else:
                rows = await conn.fetch(sql)
            
            if not rows:
                return {"columns": [], "rows": [], "row_count": 0}
            
            # Get column names from first row
            columns = list(rows[0].keys())
            
            return {
                "columns": columns,
                "rows": [list(row.values()) for row in rows],
                "row_count": len(rows)
            }
    
    async def get_tables(self) -> list[str]:
        """Get list of tables"""
        sql = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """
        result = await self.execute(sql)
        return [row[0] for row in result["rows"]]
    
    async def get_schema(self, table: str) -> list[dict]:
        """Get table schema"""
        sql = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = $1
            ORDER BY ordinal_position
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
