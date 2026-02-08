"""
Agent Repository - MySQL storage for Agent configurations
"""
import aiomysql
from typing import Optional
from datetime import datetime
import json
import os
import logging

from models.agent import Agent, DatabaseSource

logger = logging.getLogger(__name__)

class AgentRepositoryMySQL:
    """
    Repository for Agent CRUD operations using MySQL.
    
    Usage:
        repo = AgentRepositoryMySQL()
        await repo.connect()
        
        agent = await repo.create(Agent(name="Sales Agent", ...))
        agents = await repo.list_all()
    """
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        database: str = None,
        user: str = None,
        password: str = None
    ):
        self.host = host or os.getenv("AGENT_DB_HOST", "localhost")
        self.port = port or int(os.getenv("AGENT_DB_PORT", "3306"))
        self.database = database or os.getenv("AGENT_DB_NAME", "aiquery_agents")
        self.user = user or os.getenv("AGENT_DB_USER", "root")
        self.password = password or os.getenv("AGENT_DB_PASSWORD", "")
        self._pool: Optional[aiomysql.Pool] = None
    
    async def connect(self):
        """Create connection pool and initialize schema"""
        # First ensure database exists
        await self._ensure_database_exists()
        
        self._pool = await aiomysql.create_pool(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            db=self.database,
            autocommit=True,
            minsize=1,
            maxsize=10
        )
        await self._init_schema()
        logger.info(f"Connected to MySQL database: {self.database}")
    
    async def _ensure_database_exists(self):
        """Check if database exists and create if not"""
        try:
            # Connect to default 'mysql' database to check/create target db
            conn = await aiomysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db='mysql', # Connect to system db initially
                autocommit=True
            )
            async with conn.cursor() as cur:
                await cur.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            conn.close()
        except Exception as e:
            logger.error(f"Failed to ensure database existence: {e}")
            raise

    async def disconnect(self):
        """Close connection pool"""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
    
    async def _init_schema(self):
        """Initialize database schema"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                # MySQL uses different syntax than Postgres
                # 'databases' is a reserved keyword, must differ or quote
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS agents (
                        id VARCHAR(36) PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        `databases` JSON NOT NULL,
                        default_database_id VARCHAR(36),
                        auto_route BOOLEAN DEFAULT true,
                        is_active BOOLEAN DEFAULT true,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    );
                """)
                
                # Check for indexes
                try:
                    await cur.execute("CREATE INDEX idx_agents_name ON agents(name);")
                except Exception:
                    pass

                try:
                    await cur.execute("CREATE INDEX idx_agents_active ON agents(is_active);")
                except Exception:
                    pass 
    
    async def create(self, agent: Agent) -> Agent:
        """Create a new agent"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    INSERT INTO agents (id, name, description, `databases`, default_database_id, 
                                       auto_route, is_active, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    agent.id,
                    agent.name,
                    agent.description,
                    json.dumps([db.to_dict() for db in agent.databases]),
                    agent.default_database_id,
                    int(agent.auto_route),
                    int(agent.is_active),
                    agent.created_at,
                    agent.updated_at
                ))
        return agent
    
    async def get_by_id(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT * FROM agents WHERE id = %s", (agent_id,))
                row = await cur.fetchone()
                if row:
                    return self._row_to_agent(row)
        return None
    
    async def get_by_name(self, name: str) -> Optional[Agent]:
        """Get agent by name"""
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT * FROM agents WHERE name = %s", (name,))
                row = await cur.fetchone()
                if row:
                    return self._row_to_agent(row)
        return None
    
    async def list_all(self, active_only: bool = True) -> list[Agent]:
        """List all agents"""
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                if active_only:
                    await cur.execute(
                        "SELECT * FROM agents WHERE is_active = 1 ORDER BY created_at DESC"
                    )
                else:
                    await cur.execute(
                        "SELECT * FROM agents ORDER BY created_at DESC"
                    )
                rows = await cur.fetchall()
                return [self._row_to_agent(row) for row in rows]

    async def update(self, agent: Agent) -> Agent:
        """Update an existing agent"""
        agent.updated_at = datetime.now()
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    UPDATE agents 
                    SET name = %s, description = %s, `databases` = %s, 
                        default_database_id = %s, auto_route = %s, 
                        is_active = %s, updated_at = %s
                    WHERE id = %s
                """, (
                    agent.name,
                    agent.description,
                    json.dumps([db.to_dict() for db in agent.databases]),
                    agent.default_database_id,
                    int(agent.auto_route),
                    int(agent.is_active),
                    agent.updated_at,
                    agent.id
                ))
        return agent
    
    async def delete(self, agent_id: str) -> bool:
        """Delete an agent (soft delete)"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE agents SET is_active = 0, updated_at = %s WHERE id = %s",
                    (datetime.now(), agent_id)
                )
                return cur.rowcount > 0
    
    async def hard_delete(self, agent_id: str) -> bool:
        """Permanently delete an agent"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM agents WHERE id = %s",
                    (agent_id,)
                )
                return cur.rowcount > 0
    
    def _row_to_agent(self, row: dict) -> Agent:
        """Convert database row to Agent object"""
        databases_data = row["databases"]
        if isinstance(databases_data, str):
            databases_data = json.loads(databases_data)
        
        databases = [DatabaseSource.from_dict(db) for db in databases_data]
        
        # Handle 1/0 for booleans if MySQL driver returns integers
        auto_route = bool(row["auto_route"])
        is_active = bool(row["is_active"])
        
        return Agent(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            databases=databases,
            default_database_id=row["default_database_id"],
            auto_route=auto_route,
            is_active=is_active,
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )
