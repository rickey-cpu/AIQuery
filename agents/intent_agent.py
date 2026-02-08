"""
Intent Agent v2 - Enhanced with 6 intent types from FINCH
"""
from typing import Literal, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field


class IntentResult(BaseModel):
    """Result of intent analysis - expanded for FINCH intent flow"""
    intent_type: Literal[
        "data_retrieval",      # Ad-hoc queries
        "report_generation",   # Predefined reports (PO, P&L)
        "insight_generation",  # Variance analysis, trends
        "query_assistance",    # SQL help
        "allocation_explainability",  # Cost allocation explanation
        "knowledge_base",      # Policy lookup, training
        "unknown"
    ] = Field(description="Type of user intent based on FINCH categories")
    
    sub_intent: Optional[str] = Field(
        default=None,
        description="Sub-intent for more specific routing"
    )
    
    query_type: Optional[Literal["select", "aggregate", "compare", "trend", "report"]] = Field(
        default=None,
        description="Type of query if intent is data_retrieval"
    )
    
    entities: list[str] = Field(
        default_factory=list,
        description="Extracted entities (table names, metrics, filters)"
    )
    
    time_range: Optional[str] = Field(
        default=None,
        description="Time range if mentioned"
    )
    
    confidence: float = Field(
        default=0.0,
        description="Confidence score 0-1"
    )
    
    suggested_tools: list[str] = Field(
        default_factory=list,
        description="Tools to use for this intent"
    )


class IntentAgent:
    """
    Intent Agent v2 - Classifies user intent based on FINCH Intent Flow
    
    6 Intent Categories (from diagram 3):
    1. data_retrieval - Ad-hoc SQL queries
    2. report_generation - Predefined reports (PO, P&L)
    3. insight_generation - Variance analysis, executive summaries
    4. query_assistance - Help with SQL
    5. allocation_explainability - Cost allocation questions
    6. knowledge_base - Policy lookup, training
    """
    
    SYSTEM_PROMPT = """You are an Intent Analysis Agent for a Natural Language to SQL system.
Your job is to classify user questions into one of these categories:

## Intent Categories:
1. **data_retrieval** - User wants to query data (most common)
   - Sub-intents: ad_hoc_query, specific_record, filtered_list
   - Tools: column_finder, value_finder, table_rules, execute_sql

2. **report_generation** - User wants a predefined report
   - Sub-intents: po_activity, p_and_l, financial_report, sales_report
   - Tools: report_runner

3. **insight_generation** - User wants analysis or insights
   - Sub-intents: variance_explanation, trend_analysis, executive_summary
   - Tools: insight_generator, variance_analyzer

4. **query_assistance** - User needs help with SQL
   - Sub-intents: sql_help, syntax_question, optimization
   - Tools: sql_assistant

5. **allocation_explainability** - Questions about cost allocation (finance)
   - Sub-intents: rule_explanation, cost_pool_analysis
   - Tools: allocation_toolkit

6. **knowledge_base** - Policy or training questions
   - Sub-intents: policy_lookup, user_training
   - Tools: policy_finder

Also extract:
- Entities mentioned (tables, columns, values)
- Time ranges
- Query type (select, aggregate, compare, trend)

{format_instructions}
"""
    
    def __init__(self, llm):
        self.llm = llm
        self.parser = PydanticOutputParser(pydantic_object=IntentResult)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", "Analyze this question: {question}")
        ])
        self.chain = self.prompt | self.llm | self.parser
    
    async def analyze(self, question: str) -> IntentResult:
        """Analyze user question and return intent result"""
        try:
            result = await self.chain.ainvoke({
                "question": question,
                "format_instructions": self.parser.get_format_instructions()
            })
            return result
        except Exception as e:
            # Fallback to data_retrieval for SQL-like questions
            return self._fallback_analysis(question)
    
    def _fallback_analysis(self, question: str) -> IntentResult:
        """Rule-based fallback when LLM fails"""
        question_lower = question.lower()
        
        # Report keywords
        if any(kw in question_lower for kw in ['report', 'báo cáo', 'p&l', 'summary']):
            return IntentResult(
                intent_type="report_generation",
                sub_intent="general_report",
                confidence=0.6,
                suggested_tools=["report_runner"]
            )
        
        # Insight keywords
        if any(kw in question_lower for kw in ['why', 'tại sao', 'variance', 'trend', 'xu hướng']):
            return IntentResult(
                intent_type="insight_generation",
                sub_intent="variance_explanation",
                confidence=0.6,
                suggested_tools=["insight_generator"]
            )
        
        # Help keywords
        if any(kw in question_lower for kw in ['how to', 'help', 'giúp', 'cách']):
            return IntentResult(
                intent_type="query_assistance",
                sub_intent="sql_help",
                confidence=0.6,
                suggested_tools=["sql_assistant"]
            )
        
        # Policy keywords
        if any(kw in question_lower for kw in ['policy', 'chính sách', 'rule', 'quy định']):
            return IntentResult(
                intent_type="knowledge_base",
                sub_intent="policy_lookup",
                confidence=0.6,
                suggested_tools=["policy_finder"]
            )
        
        # Default to data retrieval
        query_type = "select"
        if any(kw in question_lower for kw in ['total', 'sum', 'count', 'average', 'tổng', 'đếm']):
            query_type = "aggregate"
        elif any(kw in question_lower for kw in ['compare', 'so sánh', 'vs', 'versus']):
            query_type = "compare"
        elif any(kw in question_lower for kw in ['trend', 'over time', 'by month', 'theo tháng']):
            query_type = "trend"
        
        return IntentResult(
            intent_type="data_retrieval",
            sub_intent="ad_hoc_query",
            query_type=query_type,
            confidence=0.7,
            suggested_tools=["column_finder", "value_finder", "table_rules", "execute_sql"]
        )
    
    def analyze_sync(self, question: str) -> IntentResult:
        """Synchronous version of analyze"""
        try:
            result = self.chain.invoke({
                "question": question,
                "format_instructions": self.parser.get_format_instructions()
            })
            return result
        except Exception:
            return self._fallback_analysis(question)
