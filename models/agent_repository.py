"""
Agent Repository - PostgreSQL storage for Agent configurations
"""
import asyncpg
from typing import Optional
from datetime import datetime
import json
import os

from models.agent import Agent, DatabaseSource


class AgentRepository:
    """
    Repository for Agent CRUD operations using PostgreSQL.
    
    Usage:
        repo = AgentRepository()
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
        self.port = port or int(os.getenv("AGENT_DB_PORT", "5432"))
        self.database = database or os.getenv("AGENT_DB_NAME", "aiquery_agents")
        self.user = user or os.getenv("AGENT_DB_USER", "postgres")
        self.password = password or os.getenv("AGENT_DB_PASSWORD", "postgres")
        self._pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Create connection pool"""
        self._pool = await asyncpg.create_pool(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            min_size=2,
            max_size=10
        )
        await self._init_schema()
    
    async def disconnect(self):
        """Close connection pool"""
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    async def _init_schema(self):
        """Initialize database schema"""
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    databases JSONB NOT NULL DEFAULT '[]',
                    default_database_id VARCHAR(36),
                    auto_route BOOLEAN DEFAULT true,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_agents_name ON agents(name);
                CREATE INDEX IF NOT EXISTS idx_agents_active ON agents(is_active);
            """)
    
    async def create(self, agent: Agent) -> Agent:
        """Create a new agent"""
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO agents (id, name, description, databases, default_database_id, 
                                   auto_route, is_active, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                agent.id,
                agent.name,
                agent.description,
                json.dumps([db.to_dict() for db in agent.databases]),
                agent.default_database_id,
                agent.auto_route,
                agent.is_active,
                agent.created_at,
                agent.updated_at
            )
        return agent
    
    async def get_by_id(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM agents WHERE id = $1",
                agent_id
            )
            if row:
                return self._row_to_agent(row)
        return None
    
    async def get_by_name(self, name: str) -> Optional[Agent]:
        """Get agent by name"""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM agents WHERE name = $1",
                name
            )
            if row:
                return self._row_to_agent(row)
        return None
    
    async def list_all(self, active_only: bool = True) -> list[Agent]:
        """List all agents"""
        async with self._pool.acquire() as conn:
            if active_only:
                rows = await conn.fetch(
                    "SELECT * FROM agents WHERE is_active = true ORDER BY created_at DESC"
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM agents ORDER BY created_at DESC"
                )
            return [self._row_to_agent(row) for row in rows]
    
    async def update(self, agent: Agent) -> Agent:
        """Update an existing agent"""
        agent.updated_at = datetime.now()
        async with self._pool.acquire() as conn:
            await conn.execute("""
                UPDATE agents 
                SET name = $2, description = $3, databases = $4, 
                    default_database_id = $5, auto_route = $6, 
                    is_active = $7, updated_at = $8
                WHERE id = $1
            """,
                agent.id,
                agent.name,
                agent.description,
                json.dumps([db.to_dict() for db in agent.databases]),
                agent.default_database_id,
                agent.auto_route,
                agent.is_active,
                agent.updated_at
            )
        return agent
    
    async def delete(self, agent_id: str) -> bool:
        """Delete an agent (soft delete)"""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE agents SET is_active = false, updated_at = $2 WHERE id = $1",
                agent_id,
                datetime.now()
            )
            return "UPDATE 1" in result
    
    async def hard_delete(self, agent_id: str) -> bool:
        """Permanently delete an agent"""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM agents WHERE id = $1",
                agent_id
            )
            return "DELETE 1" in result
    
    def _row_to_agent(self, row: asyncpg.Record) -> Agent:
        """Convert database row to Agent object"""
        databases_data = row["databases"]
        if isinstance(databases_data, str):
            databases_data = json.loads(databases_data)
        
        databases = [DatabaseSource.from_dict(db) for db in databases_data]
        
        return Agent(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            databases=databases,
            default_database_id=row["default_database_id"],
            auto_route=row["auto_route"],
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )


# Global repository instance
_agent_repo: Optional[AgentRepository] = None


async def init_agent_repository():
    """Initialize global agent repository"""
    global _agent_repo
    _agent_repo = AgentRepository()
    await _agent_repo.connect()
    return _agent_repo


def get_agent_repository() -> AgentRepository:
    """Get global agent repository instance"""
    return _agent_repo
