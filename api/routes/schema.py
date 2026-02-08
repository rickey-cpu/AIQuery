"""
Schema API Routes - Database schema and semantic layer management
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter()


class AliasRequest(BaseModel):
    """Request to add a semantic alias"""
    term: str = Field(..., description="Business term")
    sql_column: str = Field(..., description="SQL column name")
    table: str = Field(..., description="Table name")
    description: str = Field(default="")
    synonyms: list[str] = Field(default_factory=list)


class ValueAliasRequest(BaseModel):
    """Request to add a value alias"""
    alias: str = Field(..., description="User-facing alias")
    actual_value: str = Field(..., description="Actual database value")
    column: str = Field(..., description="Column name")
    table: str = Field(..., description="Table name")


@router.get("/schema")
async def get_schema():
    """
    Get database schema information
    """
    from rag.schema_manager import SchemaManager
    
    schema_manager = SchemaManager()
    
    tables = []
    for table_name, table_info in schema_manager.tables.items():
        tables.append({
            "name": table_name,
            "description": table_info.description,
            "columns": [
                {
                    "name": col.name,
                    "type": col.data_type,
                    "nullable": col.nullable,
                    "primary_key": col.primary_key,
                    "foreign_key": col.foreign_key,
                    "description": col.description
                }
                for col in table_info.columns
            ]
        })
    
    return {"tables": tables}


@router.get("/schema/{table_name}")
async def get_table_schema(table_name: str):
    """
    Get schema for a specific table
    """
    from rag.schema_manager import SchemaManager
    
    schema_manager = SchemaManager()
    table_info = schema_manager.get_table_info(table_name)
    
    if not table_info:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    return {
        "name": table_info.name,
        "description": table_info.description,
        "columns": [
            {
                "name": col.name,
                "type": col.data_type,
                "nullable": col.nullable,
                "primary_key": col.primary_key,
                "foreign_key": col.foreign_key,
                "description": col.description
            }
            for col in table_info.columns
        ]
    }


@router.get("/schema/semantic/mappings")
async def get_semantic_mappings():
    """
    Get all semantic layer mappings
    """
    from rag.semantic_layer import SemanticLayer
    
    semantic_layer = SemanticLayer()
    
    return {
        "term_mappings": [
            {
                "term": m.term,
                "sql_column": m.sql_column,
                "table": m.table,
                "description": m.description,
                "synonyms": m.synonyms
            }
            for m in semantic_layer.term_mappings
        ],
        "value_mappings": [
            {
                "alias": m.alias,
                "actual_value": m.actual_value,
                "column": m.column,
                "table": m.table
            }
            for m in semantic_layer.value_mappings
        ]
    }


@router.post("/schema/semantic/term")
async def add_term_mapping(request: AliasRequest):
    """
    Add a new term mapping to semantic layer
    """
    from rag.semantic_layer import SemanticLayer
    
    semantic_layer = SemanticLayer()
    semantic_layer.add_term_mapping(
        term=request.term,
        sql_column=request.sql_column,
        table=request.table,
        description=request.description,
        synonyms=request.synonyms
    )
    
    return {"message": f"Term mapping '{request.term}' added successfully"}


@router.post("/schema/semantic/value")
async def add_value_mapping(request: ValueAliasRequest):
    """
    Add a new value mapping to semantic layer
    """
    from rag.semantic_layer import SemanticLayer
    
    semantic_layer = SemanticLayer()
    semantic_layer.add_value_mapping(
        alias=request.alias,
        actual_value=request.actual_value,
        column=request.column,
        table=request.table
    )
    
    return {"message": f"Value mapping '{request.alias}' -> '{request.actual_value}' added"}
