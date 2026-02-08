"""
Models Package
"""
from .agent import Agent, DatabaseSource

# Repository factory
import os

async def init_agent_repository():
    """Initialize global agent repository based on config"""
    global _agent_repo
    
    db_type = os.getenv("AGENT_DB_TYPE", "postgresql").lower()
    
    if db_type == "mysql":
        from .agent_repository import AgentRepository  # Type hint compatibility if needed, or just use duck typing
        from .agent_repository_mysql import AgentRepositoryMySQL
        _agent_repo = AgentRepositoryMySQL()
        print(f"Agent Repository: Using MySQL ({os.getenv('AGENT_DB_HOST')})")
    else:
        # Default to PostgreSQL
        try:
            from .agent_repository import AgentRepository
            _agent_repo = AgentRepository()
            print(f"Agent Repository: Using PostgreSQL")
        except ImportError:
            print("Agent Repository: AsyncPG not installed, and MySQL not selected.")
            return None

    try:
        await _agent_repo.connect()
        return _agent_repo
    except Exception as e:
        print(f"Agent Repository: Connection failed ({e})")
        return None

def get_agent_repository():
    """Get global agent repository instance"""
    return _agent_repo

__all__ = [
    "Agent", 
    "DatabaseSource", 
    "init_agent_repository",
    "get_agent_repository"
]


