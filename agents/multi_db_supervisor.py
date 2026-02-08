"""
Multi-Database Supervisor - Extends SupervisorAgent for multi-database agents
"""
from typing import Optional, Any

from models import Agent, DatabaseSource
from .supervisor import SupervisorAgent, QueryResponse


class MultiDatabaseSupervisor:
    """
    Multi-Database Supervisor - Manages query routing across multiple databases.
    
    This class wraps the base SupervisorAgent and adds:
    1. Multiple database connectors
    2. Automatic database selection based on query
    3. Cross-database query handling
    
    Usage:
        agent = await get_agent_by_id("agent-123")
        supervisor = MultiDatabaseSupervisor(agent)
        result = await supervisor.process_query("Show me top products")
    """
    
    def __init__(
        self,
        agent: Agent,
        llm=None,
        schema_manager=None,
        semantic_layer=None,
        vector_store=None
    ):
        self.agent = agent
        self.llm = llm or self._get_default_llm()
        self.schema_manager = schema_manager
        self.semantic_layer = semantic_layer
        self.vector_store = vector_store
        
        # Create connectors for each database source
        self.connectors: dict[str, Any] = {}
        self._init_connectors()
    
    def _get_default_llm(self):
        """Get default LLM from config"""
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
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    
    def _init_connectors(self):
        """Initialize database connectors for all sources"""
        for db_source in self.agent.databases:
            try:
                connector = self._create_connector(db_source)
                self.connectors[db_source.id] = {
                    "connector": connector,
                    "source": db_source,
                    "name": db_source.name,
                    "type": db_source.db_type
                }
            except Exception as e:
                print(f"Warning: Failed to create connector for {db_source.name}: {e}")
    
    def _create_connector(self, db_source: DatabaseSource):
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
    
    async def select_database(self, question: str) -> Optional[str]:
        """
        Select the most appropriate database for a given question.
        
        Uses LLM to analyze the question and match it to available databases.
        Returns the database ID or None if no match.
        """
        if not self.agent.auto_route or len(self.connectors) <= 1:
            # Use default database
            default_db = self.agent.get_default_database()
            return default_db.id if default_db else None
        
        # Build database descriptions for LLM
        db_descriptions = []
        for db_id, info in self.connectors.items():
            source = info["source"]
            db_descriptions.append(
                f"- ID: {db_id}\n"
                f"  Name: {source.name}\n"
                f"  Type: {source.db_type}\n"
                f"  Description: {source.description or 'No description'}"
            )
        
        prompt = f"""Given the following databases, select the most appropriate one for the user's question.

Available Databases:
{chr(10).join(db_descriptions)}

User Question: {question}

Respond with ONLY the database ID that best matches the question.
If unsure, respond with the first database ID.
"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            selected_id = response.content.strip()
            
            # Validate the selected ID
            if selected_id in self.connectors:
                return selected_id
        except Exception:
            pass
        
        # Fallback to default
        default_db = self.agent.get_default_database()
        return default_db.id if default_db else None
    
    async def process_query(
        self,
        question: str,
        user_id: str = "default",
        session_id: Optional[str] = None,
        database_id: Optional[str] = None
    ) -> QueryResponse:
        """
        Process a query using the appropriate database.
        
        Args:
            question: The natural language question
            user_id: User identifier
            session_id: Session identifier
            database_id: Specific database to use (overrides auto-routing)
        """
        # Select database
        if database_id:
            target_db_id = database_id
        else:
            target_db_id = await self.select_database(question)
        
        if not target_db_id or target_db_id not in self.connectors:
            return QueryResponse(
                success=False,
                question=question,
                sql="",
                explanation="",
                data=None,
                error="No database available for this query"
            )
        
        # Get the connector
        db_info = self.connectors[target_db_id]
        connector = db_info["connector"]
        
        # Create a supervisor for this specific database
        supervisor = SupervisorAgent(
            llm=self.llm,
            db_connector=connector,
            db_type=db_info["type"],  # Pass db_type
            schema_manager=self.schema_manager,
            semantic_layer=self.semantic_layer,
            vector_store=self.vector_store
        )
        
        # Process the query
        result = await supervisor.process_query(question, user_id, session_id)
        
        # Add database info to result
        result.data = result.data or {}
        if isinstance(result.data, dict):
            result.data["_database"] = {
                "id": target_db_id,
                "name": db_info["name"],
                "type": db_info["type"]
            }
        
        return result
    
    async def process_multi_database_query(
        self,
        question: str,
        database_ids: list[str] = None,
        user_id: str = "default"
    ) -> dict:
        """
        Execute query across multiple databases and aggregate results.
        
        Useful for cross-database analytics.
        """
        target_dbs = database_ids or list(self.connectors.keys())
        results = {}
        
        for db_id in target_dbs:
            if db_id in self.connectors:
                try:
                    result = await self.process_query(
                        question,
                        user_id=user_id,
                        database_id=db_id
                    )
                    results[db_id] = {
                        "success": result.success,
                        "sql": result.sql,
                        "data": result.data,
                        "error": result.error
                    }
                except Exception as e:
                    results[db_id] = {
                        "success": False,
                        "error": str(e)
                    }
        
        return {
            "question": question,
            "databases_queried": len(results),
            "results": results
        }
    
    def get_available_databases(self) -> list[dict]:
        """Get list of available databases for this agent"""
        return [
            {
                "id": db_id,
                "name": info["name"],
                "type": info["type"],
                "is_default": db_id == self.agent.default_database_id
            }
            for db_id, info in self.connectors.items()
        ]
