"""
Agent API Routes - CRUD operations for multi-database agents
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from models import Agent, DatabaseSource, get_agent_repository

router = APIRouter()


# ==================== Request/Response Models ====================

class DatabaseSourceRequest(BaseModel):
    """Request model for database source"""
    name: str = Field(..., description="Display name for this database")
    db_type: str = Field(..., description="Database type: sqlite, mysql, postgresql, sqlserver, elasticsearch, opensearch")
    host: str = Field(default="localhost")
    port: int = Field(default=0, description="0 = use default port for db_type")
    database: str = Field(default="")
    username: str = Field(default="")
    password: str = Field(default="")
    options: dict = Field(default_factory=dict)
    is_default: bool = Field(default=False)
    description: str = Field(default="")


class AgentCreateRequest(BaseModel):
    """Request model for creating an agent"""
    name: str = Field(..., description="Agent name")
    description: str = Field(default="", description="Agent description")
    databases: list[DatabaseSourceRequest] = Field(default_factory=list)
    auto_route: bool = Field(default=True, description="Auto-select database based on query")


class AgentUpdateRequest(BaseModel):
    """Request model for updating an agent"""
    name: Optional[str] = None
    description: Optional[str] = None
    databases: Optional[list[DatabaseSourceRequest]] = None
    default_database_id: Optional[str] = None
    auto_route: Optional[bool] = None
    is_active: Optional[bool] = None


class AgentResponse(BaseModel):
    """Response model for agent"""
    id: str
    name: str
    description: str
    databases: list[dict]
    default_database_id: Optional[str]
    auto_route: bool
    is_active: bool
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class TestConnectionRequest(BaseModel):
    """Request to test database connection"""
    database_id: Optional[str] = None  # Test specific DB, or all if None


class TestConnectionResponse(BaseModel):
    """Response for connection test"""
    database_id: str
    database_name: str
    success: bool
    message: str


# ==================== API Endpoints ====================

@router.get("/agents", response_model=list[AgentResponse])
async def list_agents(active_only: bool = True):
    """List all agents"""
    try:
        repo = get_agent_repository()
        if not repo:
            raise HTTPException(status_code=503, detail="Agent repository not initialized")
        
        agents = await repo.list_all(active_only=active_only)
        return [AgentResponse(**agent.to_dict()) for agent in agents]
    except Exception as e:
        print(f"ERROR list_agents: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents", response_model=AgentResponse)
async def create_agent(request: AgentCreateRequest):
    """Create a new agent"""
    repo = get_agent_repository()
    if not repo:
        raise HTTPException(status_code=503, detail="Agent repository not initialized")
    
    # Convert request to Agent
    databases = [
        DatabaseSource(
            name=db.name,
            db_type=db.db_type,
            host=db.host,
            port=db.port,
            database=db.database,
            username=db.username,
            password=db.password,
            options=db.options,
            is_default=db.is_default,
            description=db.description
        )
        for db in request.databases
    ]
    
    agent = Agent(
        name=request.name,
        description=request.description,
        databases=databases,
        auto_route=request.auto_route
    )
    
    # Set default database
    if databases:
        default_db = next((db for db in databases if db.is_default), databases[0])
        agent.default_database_id = default_db.id
    
    created = await repo.create(agent)
    return AgentResponse(**created.to_dict())


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """Get agent by ID"""
    repo = get_agent_repository()
    if not repo:
        raise HTTPException(status_code=503, detail="Agent repository not initialized")
    
    agent = await repo.get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return AgentResponse(**agent.to_dict())


@router.put("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: str, request: AgentUpdateRequest):
    """Update an existing agent"""
    repo = get_agent_repository()
    if not repo:
        raise HTTPException(status_code=503, detail="Agent repository not initialized")
    
    agent = await repo.get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Update fields
    if request.name is not None:
        agent.name = request.name
    if request.description is not None:
        agent.description = request.description
    if request.auto_route is not None:
        agent.auto_route = request.auto_route
    if request.is_active is not None:
        agent.is_active = request.is_active
    if request.default_database_id is not None:
        agent.default_database_id = request.default_database_id
    
    if request.databases is not None:
        agent.databases = [
            DatabaseSource(
                name=db.name,
                db_type=db.db_type,
                host=db.host,
                port=db.port,
                database=db.database,
                username=db.username,
                password=db.password,
                options=db.options,
                is_default=db.is_default,
                description=db.description
            )
            for db in request.databases
        ]
    
    updated = await repo.update(agent)
    return AgentResponse(**updated.to_dict())


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str, hard: bool = False):
    """Delete an agent (soft delete by default)"""
    repo = get_agent_repository()
    if not repo:
        raise HTTPException(status_code=503, detail="Agent repository not initialized")
    
    if hard:
        success = await repo.hard_delete(agent_id)
    else:
        success = await repo.delete(agent_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"success": True, "message": "Agent deleted"}


@router.post("/agents/{agent_id}/test", response_model=list[TestConnectionResponse])
async def test_agent_connections(agent_id: str, request: TestConnectionRequest = None):
    """Test database connections for an agent"""
    repo = get_agent_repository()
    if not repo:
        raise HTTPException(status_code=503, detail="Agent repository not initialized")
    
    agent = await repo.get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    results = []
    databases_to_test = agent.databases
    
    if request and request.database_id:
        databases_to_test = [db for db in agent.databases if db.id == request.database_id]
    
    for db_source in databases_to_test:
        try:
            connector = _create_connector(db_source)
            await connector.connect()
            success = await connector.test_connection()
            await connector.disconnect()
            
            results.append(TestConnectionResponse(
                database_id=db_source.id,
                database_name=db_source.name,
                success=success,
                message="Connection successful" if success else "Connection failed"
            ))
        except Exception as e:
            results.append(TestConnectionResponse(
                database_id=db_source.id,
                database_name=db_source.name,
                success=False,
                message=str(e)
            ))
    
    return results


def _create_connector(db_source: DatabaseSource):
    """Create database connector from DatabaseSource config"""
    port = db_source.port or db_source.get_default_port()
    
    if db_source.db_type == "sqlite":
        from database.connector import DatabaseConnector
        return DatabaseConnector(db_source.database)
    
    elif db_source.db_type == "mysql":
        from database.sources.mysql import MySQLConnector
        return MySQLConnector(
            host=db_source.host,
            port=port,
            database=db_source.database,
            user=db_source.username,
            password=db_source.password
        )
    
    elif db_source.db_type == "postgresql":
        from database.sources.postgresql import PostgreSQLConnector
        return PostgreSQLConnector(
            host=db_source.host,
            port=port,
            database=db_source.database,
            user=db_source.username,
            password=db_source.password
        )
    
    elif db_source.db_type == "sqlserver":
        from database.sources.sqlserver import SQLServerConnector
        return SQLServerConnector(
            host=db_source.host,
            port=port,
            database=db_source.database,
            user=db_source.username,
            password=db_source.password,
            driver=db_source.options.get("driver", "ODBC Driver 17 for SQL Server")
        )
    
    elif db_source.db_type == "elasticsearch":
        from database.sources.elasticsearch import ElasticsearchConnector
        return ElasticsearchConnector(
            hosts=[f"http://{db_source.host}:{port}"],
            username=db_source.username,
            password=db_source.password,
            use_ssl=db_source.options.get("use_ssl", False),
            use_opensearch=False
        )
    
    elif db_source.db_type == "opensearch":
        from database.sources.opensearch import OpenSearchConnector
        return OpenSearchConnector(
            hosts=[f"http://{db_source.host}:{port}"],
            username=db_source.username,
            password=db_source.password,
            use_ssl=db_source.options.get("use_ssl", False),
            use_aws_auth=db_source.options.get("use_aws_auth", False),
            aws_region=db_source.options.get("aws_region", ""),
            aws_service=db_source.options.get("aws_service", "es")
        )
    
    else:
        raise ValueError(f"Unsupported database type: {db_source.db_type}")
