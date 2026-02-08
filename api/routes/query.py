"""
Query API Routes - Main natural language to SQL endpoint
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Optional, Any
import json

router = APIRouter()


class QueryRequest(BaseModel):
    """Request model for natural language query"""
    question: str = Field(..., description="Natural language question")
    execute: bool = Field(default=True, description="Whether to execute the SQL")
    agent_id: Optional[str] = Field(default=None, description="Agent ID for multi-database queries")
    database_id: Optional[str] = Field(default=None, description="Specific database to query (overrides auto-routing)")


class QueryResponse(BaseModel):
    """Response model for query results"""
    success: bool
    question: str
    sql: str
    explanation: str
    data: Optional[dict] = None
    error: Optional[str] = None
    warnings: list[str] = []
    database_used: Optional[dict] = None  # NEW: Info about which database was used


# In-memory query history (for demo)
_query_history: list[dict] = []


def _get_llm():
    """Get configured LLM instance"""
    from config import config
    
    if config.llm.provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=config.llm.model,
            temperature=config.llm.temperature,
            api_key=config.llm.api_key
        )
    elif config.llm.provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=config.llm.model,
            temperature=config.llm.temperature,
            google_api_key=config.llm.api_key
        )
    else:
        # Default to OpenAI
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-3.5-turbo", temperature=0)


def _get_supervisor():
    """Get configured supervisor agent"""
    from agents import SupervisorAgent
    from database import get_database
    from rag.vector_store import get_vector_store
    from rag.schema_manager import SchemaManager
    from rag.semantic_layer import SemanticLayer
    
    llm = _get_llm()
    db = get_database()
    vector_store = get_vector_store()
    schema_manager = SchemaManager()
    semantic_layer = SemanticLayer()
    
    return SupervisorAgent(
        llm=llm,
        db_connector=db,
        schema_manager=schema_manager,
        semantic_layer=semantic_layer,
        vector_store=vector_store
    )


@router.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process natural language query and return SQL + results
    
    This is the main endpoint inspired by Uber FINCH.
    Supports multi-database agents via agent_id parameter.
    """
    try:
        database_used = None
        
        # Check if using a multi-database agent
        if request.agent_id:
            from models import get_agent_repository
            from agents import MultiDatabaseSupervisor
            
            repo = get_agent_repository()
            if repo:
                agent = await repo.get_by_id(request.agent_id)
                if agent:
                    supervisor = MultiDatabaseSupervisor(agent)
                    result = await supervisor.process_query(
                        question=request.question,
                        database_id=request.database_id
                    )
                    
                    # Extract database info from result
                    if isinstance(result.data, dict) and "_database" in result.data:
                        database_used = result.data.pop("_database", None)
                else:
                    raise HTTPException(status_code=404, detail=f"Agent not found: {request.agent_id}")
            else:
                raise HTTPException(status_code=503, detail="Agent repository not available")
        else:
            # Use default supervisor (backward compatible)
            supervisor = _get_supervisor()
            result = await supervisor.process_query(request.question)
        
        response = QueryResponse(
            success=result.success,
            question=result.question,
            sql=result.sql,
            explanation=result.explanation,
            data=result.data if isinstance(result.data, dict) else None,
            error=result.error,
            warnings=result.warnings or [],
            database_used=database_used
        )
        
        # Add to history
        _query_history.append({
            "question": request.question,
            "sql": result.sql,
            "success": result.success,
            "agent_id": request.agent_id,
            "timestamp": __import__("datetime").datetime.now().isoformat()
        })
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/sql-only")
async def generate_sql_only(request: QueryRequest):
    """
    Generate SQL without executing - useful for review before execution
    """
    try:
        from agents import SQLWriterAgent
        from rag.schema_manager import SchemaManager
        from rag.semantic_layer import SemanticLayer
        from rag.vector_store import get_vector_store
        
        llm = _get_llm()
        sql_writer = SQLWriterAgent(
            llm=llm,
            schema_manager=SchemaManager(),
            semantic_layer=SemanticLayer(),
            vector_store=get_vector_store()
        )
        
        result = await sql_writer.generate_sql(request.question)
        
        return {
            "question": request.question,
            "sql": result.sql,
            "explanation": result.explanation,
            "tables_used": result.tables_used,
            "confidence": result.confidence
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/with-context")
async def query_with_context(request: QueryRequest):
    """
    Generate SQL with full Agent Context - shows how tools built context
    Like FINCH diagram: table, column, value, rules info
    """
    try:
        from agents import SQLWriterAgent
        from rag.schema_manager import SchemaManager
        from rag.semantic_layer import SemanticLayer
        from rag.vector_store import get_vector_store
        from database import get_database
        
        llm = _get_llm()
        sql_writer = SQLWriterAgent(
            llm=llm,
            schema_manager=SchemaManager(),
            semantic_layer=SemanticLayer(),
            vector_store=get_vector_store(),
            db_connector=get_database()
        )
        
        result = await sql_writer.generate_and_execute(request.question)
        
        return {
            "success": result.get("success"),
            "question": request.question,
            "sql": result.get("sql"),
            "explanation": result.get("explanation"),
            "agent_context": result.get("context"),  # NEW: Shows tool-built context
            "data": result.get("data"),
            "error": result.get("error")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools/find-column/{term}")
async def find_column(term: str):
    """
    Direct access to Column Finder Tool
    """
    from agents.tools import ColumnFinderTool
    from rag.semantic_layer import SemanticLayer
    
    tool = ColumnFinderTool(semantic_layer=SemanticLayer())
    results = tool._run(term)
    return {"term": term, "matches": results}


@router.get("/tools/find-value/{alias}")
async def find_value(alias: str):
    """
    Direct access to Value Finder Tool
    """
    from agents.tools import ValueFinderTool
    from rag.semantic_layer import SemanticLayer
    
    tool = ValueFinderTool(semantic_layer=SemanticLayer())
    result = tool._run(alias)
    return result


@router.get("/tools/table-rules/{table}")
async def get_table_rules(table: str):
    """
    Direct access to Table Rules Tool
    """
    from agents.tools import TableRulesTool
    
    tool = TableRulesTool()
    return tool._run(table)


@router.post("/query/execute")
async def execute_sql_directly(sql: str):
    """
    Execute SQL directly (for advanced users)
    """
    from database import get_database
    from agents import ValidationAgent
    
    # Validate first
    validator = ValidationAgent()
    validation = validator.validate(sql)
    
    if not validation.is_valid:
        raise HTTPException(status_code=400, detail="; ".join(validation.errors))
    
    try:
        db = get_database()
        if db:
            result = await db.execute(validation.sql)
            return {
                "sql": validation.sql,
                "data": result,
                "warnings": validation.warnings
            }
        else:
            raise HTTPException(status_code=503, detail="Database not available")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/query/stream")
async def query_stream(websocket: WebSocket):
    """
    WebSocket endpoint for streaming query results
    """
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            question = request.get("question", "")
            
            if not question:
                await websocket.send_json({"error": "Question required"})
                continue
            
            # Send processing status
            await websocket.send_json({"status": "processing", "step": "analyzing"})
            
            try:
                supervisor = _get_supervisor()
                
                # Send step updates
                await websocket.send_json({"status": "processing", "step": "generating_sql"})
                result = await supervisor.process_query(question)
                
                await websocket.send_json({
                    "status": "complete",
                    "result": result.to_dict()
                })
                
            except Exception as e:
                await websocket.send_json({"status": "error", "error": str(e)})
                
    except WebSocketDisconnect:
        pass
