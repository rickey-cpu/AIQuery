"""
Supervisor Agent v3 - Enterprise-Grade Orchestration
Enhanced with Memory, Specialized Agents, and AI Gateway
Inspired by Uber FINCH's supervisor pattern
"""
from typing import TypedDict, Annotated, Literal, Any, Optional
from dataclasses import dataclass, field
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from .intent_agent import IntentAgent, IntentResult
from .sql_writer import SQLWriterAgent, SQLResult
from .validation_agent import ValidationAgent, ValidationResult
from .report_agent import ReportAgent
from .insight_agent import InsightAgent
from .visualization_agent import VisualizationAgent


class AgentState(TypedDict):
    """State passed between agents in the workflow"""
    question: str
    user_id: str
    session_id: str
    intent: IntentResult | None
    sql_result: SQLResult | None
    validation: ValidationResult | None
    query_result: Any
    visualization: dict | None
    error: str | None
    messages: list
    conversation_context: str | None


@dataclass
class QueryResponse:
    """Final response from the supervisor"""
    success: bool
    question: str
    sql: str
    explanation: str
    data: Any
    intent_type: str = "data_retrieval"
    visualization: dict = None
    error: str | None = None
    warnings: list[str] = None
    cached: bool = False
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "question": self.question,
            "sql": self.sql,
            "explanation": self.explanation,
            "data": self.data,
            "intent_type": self.intent_type,
            "visualization": self.visualization,
            "error": self.error,
            "warnings": self.warnings or [],
            "cached": self.cached
        }


class SupervisorAgent:
    """
    Supervisor Agent v3 - Enterprise Orchestration
    
    Enhanced Features (FINCH-inspired):
    1. Conversation Memory - Multi-turn context
    2. AI Gateway - Rate limiting, caching, fallback
    3. Specialized Agents - Report, Insight, Viz
    4. Feedback Learning - Self-improvement
    5. Query Caching - Fast repeated queries
    
    Workflow:
    1. Check Cache → Return if hit
    2. Load Memory → Get conversation context  
    3. Intent Analysis → Route to appropriate agent
    4. SQL/Report/Insight Generation
    5. Validation → Check safety
    6. Execution → Run query
    7. Visualization → Generate charts
    8. Feedback → Record for learning
    9. Update Memory → Store context
    """
    
    def __init__(
        self,
        llm=None,
        db_connector=None,
        db_type: str = "generic",  # Added db_type
        schema_manager=None,
        semantic_layer=None,
        vector_store=None,
        use_gateway: bool = True,
        use_memory: bool = True,
        use_cache: bool = True
    ):
        self.db_connector = db_connector
        self.db_type = db_type
        self.use_gateway = use_gateway
        self.use_memory = use_memory
        self.use_cache = use_cache
        
        # Get LLM from gateway or use provided
        if use_gateway:
            from services.ai_gateway import get_gateway
            self.gateway = get_gateway()
            self.llm = llm  # Still need for agents
        else:
            self.gateway = None
            self.llm = llm
        
        # Initialize memory and feedback
        if use_memory:
            from services.memory import get_memory
            self.memory = get_memory()
        else:
            self.memory = None
        
        if use_cache:
            from services.cache import get_cache
            self.cache = get_cache()
        else:
            self.cache = None
        
        from services.feedback import get_feedback
        self.feedback = get_feedback()
        
        # Initialize sub-agents
        self.intent_agent = IntentAgent(llm)
        self.sql_writer = SQLWriterAgent(
            llm, 
            schema_manager=schema_manager,
            semantic_layer=semantic_layer,
            vector_store=vector_store,
            db_connector=db_connector,
            db_type=db_type  # Pass db_type
        )
        self.validation_agent = ValidationAgent()
        self.report_agent = ReportAgent(llm)
        self.insight_agent = InsightAgent(llm, db_connector)
        self.viz_agent = VisualizationAgent()
        
        # Build the workflow graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build enhanced LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("check_cache", self._check_cache)
        workflow.add_node("load_memory", self._load_memory)
        workflow.add_node("analyze_intent", self._analyze_intent)
        workflow.add_node("generate_sql", self._generate_sql)
        workflow.add_node("generate_report", self._generate_report)
        workflow.add_node("generate_insight", self._generate_insight)
        workflow.add_node("validate_sql", self._validate_sql)
        workflow.add_node("execute_query", self._execute_query)
        workflow.add_node("generate_visualization", self._generate_visualization)
        workflow.add_node("record_feedback", self._record_feedback)
        workflow.add_node("handle_error", self._handle_error)
        
        # Set entry point
        workflow.set_entry_point("check_cache")
        
        # Add edges
        workflow.add_conditional_edges(
            "check_cache",
            self._route_after_cache,
            {
                "cache_hit": END,
                "cache_miss": "load_memory"
            }
        )
        
        workflow.add_edge("load_memory", "analyze_intent")
        
        # Route based on intent
        workflow.add_conditional_edges(
            "analyze_intent",
            self._route_after_intent,
            {
                "data_retrieval": "generate_sql",
                "report_generation": "generate_report",
                "insight_generation": "generate_insight",
                "query_assistance": "generate_sql",
                "error": "handle_error"
            }
        )
        
        workflow.add_edge("generate_report", "validate_sql")
        workflow.add_edge("generate_insight", "validate_sql")
        workflow.add_edge("generate_sql", "validate_sql")
        
        workflow.add_conditional_edges(
            "validate_sql",
            self._route_after_validation,
            {
                "execute": "execute_query",
                "error": "handle_error"
            }
        )
        
        workflow.add_edge("execute_query", "generate_visualization")
        workflow.add_edge("generate_visualization", "record_feedback")
        workflow.add_edge("record_feedback", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile()
    
    async def _check_cache(self, state: AgentState) -> AgentState:
        """Node: Check query cache"""
        if self.cache:
            cached = self.cache.get(state["question"])
            if cached:
                state["query_result"] = cached.get("result")
                state["sql_result"] = SQLResult(
                    sql=cached.get("sql", ""),
                    explanation="(cached result)",
                    confidence=1.0
                )
        return state
    
    def _route_after_cache(self, state: AgentState) -> str:
        """Router: Check if cache hit"""
        if state.get("query_result"):
            return "cache_hit"
        return "cache_miss"
    
    async def _load_memory(self, state: AgentState) -> AgentState:
        """Node: Load conversation context"""
        if self.memory:
            user_id = state.get("user_id", "default")
            session_id = state.get("session_id")
            
            # Get context from memory
            context = self.memory.get_context_for_prompt(user_id, session_id)
            state["conversation_context"] = context
            
            # Record this message
            self.memory.add_message(
                user_id=user_id,
                role="user",
                content=state["question"],
                session_id=session_id
            )
        return state
    
    async def _analyze_intent(self, state: AgentState) -> AgentState:
        """Node: Analyze user intent"""
        try:
            intent = await self.intent_agent.analyze(state["question"])
            state["intent"] = intent
        except Exception as e:
            state["error"] = f"Intent analysis failed: {str(e)}"
        return state
    
    def _route_after_intent(self, state: AgentState) -> str:
        """Router: Route to appropriate agent based on intent"""
        if state.get("error"):
            return "error"
        
        intent = state.get("intent")
        if not intent:
            return "error"
        
        intent_type = intent.intent_type
        
        # Map FINCH intents to agents
        if intent_type in ["data_retrieval", "query_assistance"]:
            return "data_retrieval"
        elif intent_type == "report_generation":
            return "report_generation"
        elif intent_type == "insight_generation":
            return "insight_generation"
        else:
            return "data_retrieval"  # Default
    
    async def _generate_sql(self, state: AgentState) -> AgentState:
        """Node: Generate SQL from question"""
        try:
            # Include conversation context if available
            context = state.get("conversation_context", "")
            question = state["question"]
            if context:
                question = f"{context}\n\nCurrent question: {question}"
            
            sql_result = await self.sql_writer.generate_sql(question)
            state["sql_result"] = sql_result
        except Exception as e:
            state["error"] = f"SQL generation failed: {str(e)}"
        return state
    
    async def _generate_report(self, state: AgentState) -> AgentState:
        """Node: Generate report using Report Agent"""
        try:
            report = await self.report_agent.generate_report(state["question"])
            
            if "sql_queries" in report and report["sql_queries"]:
                state["sql_result"] = SQLResult(
                    sql=report["sql_queries"][0],
                    explanation=report.get("explanation", ""),
                    confidence=0.9
                )
            else:
                state["error"] = report.get("error", "No SQL generated")
        except Exception as e:
            state["error"] = f"Report generation failed: {str(e)}"
        return state
    
    async def _generate_insight(self, state: AgentState) -> AgentState:
        """Node: Generate insight using Insight Agent"""
        try:
            insight = await self.insight_agent.generate_insight(state["question"])
            
            if "sql_queries" in insight and insight["sql_queries"]:
                state["sql_result"] = SQLResult(
                    sql=insight["sql_queries"][0],
                    explanation=insight.get("summary", ""),
                    confidence=0.85
                )
            else:
                state["error"] = "No SQL generated from insight"
        except Exception as e:
            state["error"] = f"Insight generation failed: {str(e)}"
        return state
    
    async def _validate_sql(self, state: AgentState) -> AgentState:
        """Node: Validate generated SQL"""
        sql_result = state.get("sql_result")
        
        if not sql_result or not sql_result.sql:
            state["error"] = "No SQL generated"
            return state
            
        # Check if SQL is actually an error report
        if sql_result.sql.strip().startswith("/*\nERROR"):
            state["error"] = "SQL Generation Failed (see details in SQL console)"
            return state
        
        validation = self.validation_agent.validate(sql_result.sql)
        state["validation"] = validation
        
        if not validation.is_valid:
            state["error"] = "; ".join(validation.errors)
        
        return state
    
    def _route_after_validation(self, state: AgentState) -> str:
        """Router: Decide next step after validation"""
        validation = state.get("validation")
        if not validation or not validation.is_valid:
            return "error"
        return "execute"
    
    async def _execute_query(self, state: AgentState) -> AgentState:
        """Node: Execute validated SQL"""
        validation = state.get("validation")
        if not validation:
            state["error"] = "No validated SQL"
            return state
        
        try:
            if self.db_connector:
                result = await self.db_connector.execute(validation.sql)
                state["query_result"] = result
            else:
                # Demo mode
                state["query_result"] = {
                    "columns": ["id", "name", "value"],
                    "rows": [
                        [1, "Sample 1", 100],
                        [2, "Sample 2", 200],
                        [3, "Sample 3", 300]
                    ],
                    "row_count": 3
                }
        except Exception as e:
            state["error"] = f"Query execution failed: {str(e)}"
        
        return state
    
    async def _generate_visualization(self, state: AgentState) -> AgentState:
        """Node: Generate visualization for results"""
        query_result = state.get("query_result")
        if query_result and not state.get("error"):
            viz_config = self.viz_agent.generate_chart_config(
                query_result,
                title=state["question"][:50]
            )
            state["visualization"] = viz_config.to_dict()
        return state
    
    async def _record_feedback(self, state: AgentState) -> AgentState:
        """Node: Record query for feedback learning"""
        sql_result = state.get("sql_result")
        if sql_result and self.feedback:
            self.feedback.record_query(
                question=state["question"],
                sql=sql_result.sql,
                user_id=state.get("user_id", "anonymous"),
                was_executed=True,
                execution_success=not state.get("error")
            )
        
        # Update memory with response
        if self.memory and not state.get("error"):
            user_id = state.get("user_id", "default")
            session_id = state.get("session_id")
            
            self.memory.add_message(
                user_id=user_id,
                role="assistant",
                content=sql_result.explanation if sql_result else "",
                session_id=session_id,
                metadata={
                    "sql": sql_result.sql if sql_result else "",
                    "result_summary": f"{state.get('query_result', {}).get('row_count', 0)} rows"
                }
            )
        
        # Cache the result
        if self.cache and not state.get("error"):
            validation = state.get("validation")
            self.cache.set(
                state["question"],
                validation.sql if validation else "",
                state.get("query_result", {})
            )
        
        return state
    
    async def _handle_error(self, state: AgentState) -> AgentState:
        """Node: Handle errors"""
        if not state.get("error"):
            state["error"] = "Unknown error occurred"
        return state
    
    async def process_query(
        self,
        question: str,
        user_id: str = "default",
        session_id: Optional[str] = None
    ) -> QueryResponse:
        """Process a natural language query through the full workflow"""
        initial_state: AgentState = {
            "question": question,
            "user_id": user_id,
            "session_id": session_id or "",
            "intent": None,
            "sql_result": None,
            "validation": None,
            "query_result": None,
            "visualization": None,
            "error": None,
            "messages": [HumanMessage(content=question)],
            "conversation_context": None
        }
        
        # Run the workflow
        final_state = await self.graph.ainvoke(initial_state)
        
        # Build response
        if final_state.get("error"):
            return QueryResponse(
                success=False,
                question=question,
                sql=final_state.get("sql_result").sql if final_state.get("sql_result") else "",
                explanation="",
                data=None,
                error=final_state["error"]
            )
        
        sql_result = final_state.get("sql_result")
        validation = final_state.get("validation")
        intent = final_state.get("intent")
        
        return QueryResponse(
            success=True,
            question=question,
            sql=validation.sql if validation else "",
            explanation=sql_result.explanation if sql_result else "",
            data=final_state.get("query_result"),
            intent_type=intent.intent_type if intent else "data_retrieval",
            visualization=final_state.get("visualization"),
            warnings=validation.warnings if validation else [],
            cached=False
        )
    
    def process_query_sync(self, question: str) -> QueryResponse:
        """Synchronous version for simple use cases"""
        import asyncio
        return asyncio.run(self.process_query(question))
