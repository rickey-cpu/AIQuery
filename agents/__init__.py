"""
AI Query Agent - Agents Package v3
Enhanced with specialized agents from FINCH architecture
"""
from .supervisor import SupervisorAgent
from .intent_agent import IntentAgent
from .sql_writer import SQLWriterAgent
from .validation_agent import ValidationAgent
from .report_agent import ReportAgent
from .insight_agent import InsightAgent
from .visualization_agent import VisualizationAgent
from .multi_db_supervisor import MultiDatabaseSupervisor

__all__ = [
    # Core Agents
    "SupervisorAgent",
    "MultiDatabaseSupervisor",
    "IntentAgent", 
    "SQLWriterAgent",
    "ValidationAgent",
    # Specialized Agents (FINCH)
    "ReportAgent",
    "InsightAgent",
    "VisualizationAgent"
]

