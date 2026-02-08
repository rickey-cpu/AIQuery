"""
Supervisor Agent - Orchestrates the multi-agent workflow using LangGraph
Main coordinator inspired by Uber FINCH's supervisor pattern
"""
from typing import TypedDict, Annotated, Literal, Any
from dataclasses import dataclass
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from .intent_agent import IntentAgent, IntentResult
from .sql_writer import SQLWriterAgent, SQLResult
from .validation_agent import ValidationAgent, ValidationResult


class AgentState(TypedDict):
    """State passed between agents in the workflow"""
    question: str
    intent: IntentResult | None
    sql_result: SQLResult | None
    validation: ValidationResult | None
    query_result: Any
    error: str | None
    messages: list


@dataclass
class QueryResponse:
    """Final response from the supervisor"""
    success: bool
    question: str
    sql: str
    explanation: str
    data: Any
    error: str | None = None
    warnings: list[str] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "question": self.question,
            "sql": self.sql,
            "explanation": self.explanation,
            "data": self.data,
            "error": self.error,
            "warnings": self.warnings or []
        }


class SupervisorAgent:
    """
    Supervisor Agent - Orchestrates the query workflow
    
    Workflow:
    1. Intent Analysis → Understand what user wants
    2. SQL Generation → Convert to SQL using semantic layer
    3. Validation → Check SQL safety and correctness  
    4. Execution → Run query and return results
    
    Uses LangGraph for workflow management
    """
    
    def __init__(self, llm, db_connector=None, schema_manager=None, 
                 semantic_layer=None, vector_store=None):
        self.llm = llm
        self.db_connector = db_connector
        
        # Initialize sub-agents
        self.intent_agent = IntentAgent(llm)
        self.sql_writer = SQLWriterAgent(
            llm, 
            schema_manager=schema_manager,
            semantic_layer=semantic_layer,
            vector_store=vector_store
        )
        self.validation_agent = ValidationAgent()
        
        # Build the workflow graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("analyze_intent", self._analyze_intent)
        workflow.add_node("generate_sql", self._generate_sql)
        workflow.add_node("validate_sql", self._validate_sql)
        workflow.add_node("execute_query", self._execute_query)
        workflow.add_node("handle_error", self._handle_error)
        
        # Set entry point
        workflow.set_entry_point("analyze_intent")
        
        # Add edges
        workflow.add_conditional_edges(
            "analyze_intent",
            self._route_after_intent,
            {
                "query": "generate_sql",
                "help": END,
                "error": "handle_error"
            }
        )
        
        workflow.add_edge("generate_sql", "validate_sql")
        
        workflow.add_conditional_edges(
            "validate_sql",
            self._route_after_validation,
            {
                "execute": "execute_query",
                "error": "handle_error"
            }
        )
        
        workflow.add_edge("execute_query", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile()
    
    async def _analyze_intent(self, state: AgentState) -> AgentState:
        """Node: Analyze user intent"""
        try:
            intent = await self.intent_agent.analyze(state["question"])
            state["intent"] = intent
        except Exception as e:
            state["error"] = f"Intent analysis failed: {str(e)}"
        return state
    
    def _route_after_intent(self, state: AgentState) -> str:
        """Router: Decide next step after intent analysis"""
        if state.get("error"):
            return "error"
        
        intent = state.get("intent")
        if not intent:
            return "error"
        
        if intent.intent_type == "query":
            return "query"
        elif intent.intent_type == "help":
            return "help"
        else:
            return "error"
    
    async def _generate_sql(self, state: AgentState) -> AgentState:
        """Node: Generate SQL from question"""
        try:
            sql_result = await self.sql_writer.generate_sql(state["question"])
            state["sql_result"] = sql_result
        except Exception as e:
            state["error"] = f"SQL generation failed: {str(e)}"
        return state
    
    async def _validate_sql(self, state: AgentState) -> AgentState:
        """Node: Validate generated SQL"""
        sql_result = state.get("sql_result")
        if not sql_result or not sql_result.sql:
            state["error"] = "No SQL generated"
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
                # Demo mode - return sample data
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
    
    async def _handle_error(self, state: AgentState) -> AgentState:
        """Node: Handle errors"""
        if not state.get("error"):
            state["error"] = "Unknown error occurred"
        return state
    
    async def process_query(self, question: str) -> QueryResponse:
        """Process a natural language query through the full workflow"""
        initial_state: AgentState = {
            "question": question,
            "intent": None,
            "sql_result": None,
            "validation": None,
            "query_result": None,
            "error": None,
            "messages": [HumanMessage(content=question)]
        }
        
        # Run the workflow
        final_state = await self.graph.ainvoke(initial_state)
        
        # Build response
        if final_state.get("error"):
            return QueryResponse(
                success=False,
                question=question,
                sql=final_state.get("sql_result", {}).get("sql", "") if final_state.get("sql_result") else "",
                explanation="",
                data=None,
                error=final_state["error"]
            )
        
        sql_result = final_state.get("sql_result")
        validation = final_state.get("validation")
        
        return QueryResponse(
            success=True,
            question=question,
            sql=validation.sql if validation else "",
            explanation=sql_result.explanation if sql_result else "",
            data=final_state.get("query_result"),
            warnings=validation.warnings if validation else []
        )
    
    def process_query_sync(self, question: str) -> QueryResponse:
        """Synchronous version for simple use cases"""
        import asyncio
        return asyncio.run(self.process_query(question))
