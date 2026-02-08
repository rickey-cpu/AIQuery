"""
History API Routes - Query history and favorites
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

router = APIRouter()

# In-memory storage (replace with database in production)
_query_history: list[dict] = []
_favorites: list[dict] = []


class FavoriteRequest(BaseModel):
    """Request to save a favorite query"""
    name: str = Field(..., description="Name for the saved query")
    question: str = Field(..., description="Natural language question")
    sql: str = Field(..., description="Generated SQL")


@router.get("/history")
async def get_query_history(limit: int = 50, offset: int = 0):
    """
    Get query history
    """
    # In production, fetch from database
    total = len(_query_history)
    items = _query_history[offset:offset + limit]
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items
    }


@router.delete("/history")
async def clear_history():
    """
    Clear query history
    """
    global _query_history
    _query_history = []
    return {"message": "History cleared"}


@router.get("/history/favorites")
async def get_favorites():
    """
    Get saved favorite queries
    """
    return {"favorites": _favorites}


@router.post("/history/favorites")
async def add_favorite(request: FavoriteRequest):
    """
    Save a query as favorite
    """
    favorite = {
        "id": len(_favorites) + 1,
        "name": request.name,
        "question": request.question,
        "sql": request.sql,
        "created_at": datetime.now().isoformat()
    }
    _favorites.append(favorite)
    
    return {"message": "Favorite saved", "favorite": favorite}


@router.delete("/history/favorites/{favorite_id}")
async def delete_favorite(favorite_id: int):
    """
    Delete a favorite query
    """
    global _favorites
    _favorites = [f for f in _favorites if f.get("id") != favorite_id]
    return {"message": f"Favorite {favorite_id} deleted"}


@router.get("/history/examples")
async def get_sql_examples():
    """
    Get SQL examples from vector store
    """
    from rag.vector_store import get_vector_store
    
    vector_store = get_vector_store()
    if vector_store:
        examples = vector_store.get_all_examples()
        return {"examples": examples}
    
    return {"examples": []}


@router.post("/history/examples")
async def add_sql_example(question: str, sql: str):
    """
    Add a new SQL example to vector store
    """
    from rag.vector_store import get_vector_store
    
    vector_store = get_vector_store()
    if vector_store:
        vector_store.add_examples([{"question": question, "sql": sql}])
        return {"message": "Example added"}
    
    raise HTTPException(status_code=503, detail="Vector store not available")
