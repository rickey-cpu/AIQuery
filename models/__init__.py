"""
Models Package
"""
from .agent import Agent, DatabaseSource

# AgentRepository requires asyncpg - make it optional
try:
    from .agent_repository import AgentRepository, init_agent_repository, get_agent_repository
    _has_agent_repo = True
except ImportError:
    AgentRepository = None
    init_agent_repository = None
    get_agent_repository = lambda: None
    _has_agent_repo = False

__all__ = [
    "Agent", 
    "DatabaseSource", 
    "AgentRepository",
    "init_agent_repository",
    "get_agent_repository"
]


