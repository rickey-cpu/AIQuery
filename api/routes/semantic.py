from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from rag.semantic_layer import SemanticLayer, SemanticEntity, SemanticMetric
from rag.opensearch_store import OpenSearchStore

router = APIRouter(prefix="/agents/{agent_id}/semantic", tags=["Semantic Management"])

# --- Models ---

class EntityModel(BaseModel):
    name: str
    table_name: str
    primary_key: str
    description: str
    synonyms: List[str] = []

class MetricModel(BaseModel):
    name: str
    definition: str
    description: str
    condition: Optional[str] = None
    synonyms: List[str] = []

# --- Helpers ---

def get_layer(agent_id: str) -> SemanticLayer:
    """Get Semantic Layer instance for an agent (without loading default mappings)"""
    # We initialize a 'blank' layer first, then populate it from OpenSearch
    # In a real app, we might want to cache this or load from a permanent DB
    # For now, we rely on OpenSearch as the persistence layer for agent definitions
    layer = SemanticLayer(agent_id=agent_id)
    return layer

# --- Endpoints ---

@router.get("/entities", response_model=List[EntityModel])
async def list_entities(agent_id: str):
    """List all entities for an agent"""
    store = OpenSearchStore()
    # Fetch all definitions of type 'entity' for this agent
    # We use a large limit for now
    results = store.search_definitions(query="*", k=100, agent_id=agent_id)
    
    entities = []
    for res in results:
        if res.get("type") == "entity":
            # Reconstruction from search result (simplified)
            # In a full impl, we'd store the full JSON in OpenSearch source
            # Here we just return what we have
             entities.append(EntityModel(
                name=res.get("sql", ""),
                table_name="?", # Details missing in simple index, would need full storage
                primary_key="?",
                description=res.get("question", ""),
                synonyms=[]
            ))
    return entities

@router.post("/entities")
async def create_entity(agent_id: str, entity: EntityModel):
    """Create a new semantic entity for an agent"""
    store = OpenSearchStore()
    
    # Create valid SemanticEntity object
    obj = SemanticEntity(
        name=entity.name,
        table_name=entity.table_name,
        primary_key=entity.primary_key,
        description=entity.description,
        synonyms=entity.synonyms,
        agent_id=agent_id
    )
    
    # Index into OpenSearch
    # We construct a rich text representation for search
    text = f"Entity: {obj.name}. {obj.description}. Synonyms: {', '.join(obj.synonyms)}"
    
    definition = {
        "text": text,
        "sql": obj.name,
        "type": "entity",
        "description": obj.description
    }
    
    store.add_definitions([definition], agent_id=agent_id)
    return {"status": "success", "message": f"Entity '{entity.name}' added"}

@router.put("/entities")
async def update_entity(agent_id: str, entity: EntityModel):
    """Update an existing semantic entity"""
    return await create_entity(agent_id, entity)

@router.delete("/entities/{name}")
async def delete_entity(agent_id: str, name: str):
    """Delete an entity"""
    store = OpenSearchStore()
    success = store.delete_definition(name, "entity", agent_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Entity '{name}' not found or could not be deleted")
    return {"status": "success", "message": f"Entity '{name}' deleted"}

@router.get("/metrics", response_model=List[MetricModel])
async def list_metrics(agent_id: str):
    """List all metrics for an agent"""
    store = OpenSearchStore()
    results = store.search_definitions(query="*", k=100, agent_id=agent_id)
    
    metrics = []
    for res in results:
        if res.get("type") == "metric":
             metrics.append(MetricModel(
                name=res.get("sql", ""),
                definition="?",
                description=res.get("question", ""),
                synonyms=[]
            ))
    return metrics

@router.post("/metrics")
async def create_metric(agent_id: str, metric: MetricModel):
    """Create a new metric for an agent"""
    store = OpenSearchStore()
    
    obj = SemanticMetric(
        name=metric.name,
        definition=metric.definition,
        description=metric.description,
        condition=metric.condition,
        synonyms=metric.synonyms,
        agent_id=agent_id
    )
    
    text = f"Metric: {obj.name}. {obj.description}. Synonyms: {', '.join(obj.synonyms)}"
    
    definition = {
        "text": text,
        "sql": obj.name,
        "type": "metric",
        "description": obj.description
    }
    
    store.add_definitions([definition], agent_id=agent_id)
    return {"status": "success", "message": f"Metric '{metric.name}' added"}

@router.put("/metrics")
async def update_metric(agent_id: str, metric: MetricModel):
    """Update an existing metric"""
    return await create_metric(agent_id, metric)

@router.delete("/metrics/{name}")
async def delete_metric(agent_id: str, name: str):
    """Delete a metric"""
    store = OpenSearchStore()
    success = store.delete_definition(name, "metric", agent_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Metric '{name}' not found or could not be deleted")
    return {"status": "success", "message": f"Metric '{name}' deleted"}
