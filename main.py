"""
AI Query Agent - Main Entry Point
Natural Language to SQL conversion powered by LLM
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from config import config, load_config_from_env


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    print("🚀 Starting AI Query Agent...")
    load_config_from_env()
    
    # Initialize components
    from database.connector import init_database
    from rag.vector_store import init_vector_store
    
    await init_database()
    init_vector_store()
    
    print("✅ AI Query Agent ready!")
    print(f"📊 Database: {config.database.type}")
    print(f"🤖 LLM Provider: {config.llm.provider} ({config.llm.model})")
    
    yield
    
    # Shutdown
    print("👋 Shutting down AI Query Agent...")


# Create FastAPI app
app = FastAPI(
    title="AI Query Agent",
    description="Natural Language to SQL conversion powered by LLM - Inspired by Uber FINCH",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Import and include routers
from api.routes import query, schema, history

app.include_router(query.router, prefix="/api", tags=["Query"])
app.include_router(schema.router, prefix="/api", tags=["Schema"])
app.include_router(history.router, prefix="/api", tags=["History"])


@app.get("/")
async def root():
    """Root endpoint - redirect to frontend"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "llm_provider": config.llm.provider,
        "database_type": config.database.type
    }


@app.get("/api/health")
async def api_health_check():
    """API health check for Vue frontend"""
    return {
        "status": "healthy",
        "version": "3.0.0",
        "provider": config.llm.provider
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.api.debug
    )
