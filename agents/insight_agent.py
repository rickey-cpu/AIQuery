"""
Insight Agent - Generate Insights and Analysis
Inspired by Uber FINCH's Insight Generation intent
"""
from typing import Optional, Any
from dataclasses import dataclass
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field


class InsightResult(BaseModel):
    """Insight generation result"""
    insight_type: str = Field(description="Type: variance, trend, anomaly, comparison")
    title: str = Field(description="Brief insight title")
    summary: str = Field(description="Natural language insight summary")
    sql_queries: list[str] = Field(description="SQL queries for data")
    key_findings: list[str] = Field(description="Key findings list")
    recommendations: list[str] = Field(default=[], description="Recommendations")


class InsightAgent:
    """
    Insight Agent - Analytics and Explanation
    
    Features (inspired by FINCH):
    - Variance explanation ("Why did revenue drop?")
    - Trend detection
    - Anomaly highlighting
    - Period comparisons
    - Executive summary generation
    
    Sub-intents handled:
    - Variance Explanation
    - Trend Analysis
    - Executive Summary
    - Anomaly Detection
    """
    
    SYSTEM_PROMPT = """You are an Insight Generator Agent specializing in data analysis.

Given a question about data insights, you should:
1. Identify what type of insight is needed
2. Generate SQL queries to gather required data
3. Structure the analysis into clear findings

Question: {question}

Available context:
{context}

Generate the insight analysis in JSON format:
{format_instructions}
"""
    
    def __init__(self, llm=None, db_connector=None):
        self.llm = llm
        self.db_connector = db_connector
        self.parser = JsonOutputParser(pydantic_object=InsightResult)
    
    def _detect_insight_type(self, question: str) -> str:
        """Detect what type of insight is requested"""
        question_lower = question.lower()
        
        variance_words = ["why", "tại sao", "drop", "increase", "change", 
                         "giảm", "tăng", "thay đổi", "differ", "khác"]
        trend_words = ["trend", "xu hướng", "over time", "theo thời gian", 
                      "growth", "tăng trưởng"]
        anomaly_words = ["unusual", "bất thường", "anomaly", "outlier", 
                        "strange", "lạ"]
        comparison_words = ["compare", "so sánh", "vs", "versus", "difference",
                           "between", "giữa"]
        
        if any(w in question_lower for w in variance_words):
            return "variance"
        elif any(w in question_lower for w in trend_words):
            return "trend"
        elif any(w in question_lower for w in anomaly_words):
            return "anomaly"
        elif any(w in question_lower for w in comparison_words):
            return "comparison"
        else:
            return "summary"
    
    async def generate_insight(
        self,
        question: str,
        context: Optional[dict] = None
    ) -> dict:
        """Generate insight for the question"""
        insight_type = self._detect_insight_type(question)
        context = context or {}
        
        # Generate insight based on type
        if insight_type == "variance":
            return await self._variance_analysis(question, context)
        elif insight_type == "trend":
            return await self._trend_analysis(question, context)
        elif insight_type == "comparison":
            return await self._comparison_analysis(question, context)
        else:
            return await self._general_insight(question, context)
    
    async def _variance_analysis(self, question: str, context: dict) -> dict:
        """Analyze variance and explain changes"""
        # Generate SQL for period comparison
        sql_queries = [
            # Current period
            """
            SELECT 
                SUM(total_amount) as current_revenue,
                COUNT(*) as current_orders
            FROM orders
            WHERE order_date >= date('now', '-30 days')
            """,
            # Previous period
            """
            SELECT 
                SUM(total_amount) as previous_revenue,
                COUNT(*) as previous_orders
            FROM orders
            WHERE order_date >= date('now', '-60 days') 
              AND order_date < date('now', '-30 days')
            """,
            # Breakdown by category
            """
            SELECT 
                c.city,
                SUM(CASE WHEN o.order_date >= date('now', '-30 days') 
                    THEN o.total_amount ELSE 0 END) as current,
                SUM(CASE WHEN o.order_date < date('now', '-30 days') 
                    THEN o.total_amount ELSE 0 END) as previous
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            WHERE o.order_date >= date('now', '-60 days')
            GROUP BY c.city
            ORDER BY (current - previous) ASC
            LIMIT 5
            """
        ]
        
        # Execute queries if connector available
        results = []
        if self.db_connector:
            for sql in sql_queries:
                try:
                    result = await self.db_connector.execute(sql)
                    results.append(result)
                except Exception as e:
                    results.append({"error": str(e)})
        
        # Use LLM to generate insight if available
        if self.llm:
            return await self._llm_insight(question, sql_queries, results)
        
        return {
            "insight_type": "variance",
            "title": "Variance Analysis",
            "summary": "Variance analysis requires data execution",
            "sql_queries": sql_queries,
            "key_findings": ["Execute queries to see findings"],
            "recommendations": []
        }
    
    async def _trend_analysis(self, question: str, context: dict) -> dict:
        """Analyze trends over time"""
        sql_queries = [
            """
            SELECT 
                strftime('%Y-%m', order_date) as month,
                SUM(total_amount) as revenue,
                COUNT(*) as orders,
                AVG(total_amount) as avg_order
            FROM orders
            WHERE order_date >= date('now', '-12 months')
            GROUP BY month
            ORDER BY month
            """
        ]
        
        return {
            "insight_type": "trend",
            "title": "Trend Analysis",
            "summary": "12-month trend analysis",
            "sql_queries": sql_queries,
            "key_findings": ["Monthly revenue trend", "Order volume trend"],
            "recommendations": []
        }
    
    async def _comparison_analysis(self, question: str, context: dict) -> dict:
        """Compare different segments or periods"""
        sql_queries = [
            """
            SELECT 
                c.city,
                COUNT(*) as orders,
                SUM(o.total_amount) as revenue,
                AVG(o.total_amount) as avg_order
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            GROUP BY c.city
            ORDER BY revenue DESC
            """
        ]
        
        return {
            "insight_type": "comparison",
            "title": "Segment Comparison",
            "summary": "Comparison across segments",
            "sql_queries": sql_queries,
            "key_findings": [],
            "recommendations": []
        }
    
    async def _general_insight(self, question: str, context: dict) -> dict:
        """Generate general insight"""
        if self.llm:
            return await self._llm_insight(question, [], [])
        
        return {
            "insight_type": "summary",
            "title": "General Insight",
            "summary": "Please specify what insight you need",
            "sql_queries": [],
            "key_findings": [],
            "recommendations": []
        }
    
    async def _llm_insight(
        self,
        question: str,
        sql_queries: list[str],
        results: list
    ) -> dict:
        """Use LLM to generate insight"""
        prompt = ChatPromptTemplate.from_template(self.SYSTEM_PROMPT)
        
        context = {
            "sql_queries": sql_queries,
            "results": results
        }
        
        chain = prompt | self.llm | self.parser
        
        try:
            result = await chain.ainvoke({
                "question": question,
                "context": str(context),
                "format_instructions": self.parser.get_format_instructions()
            })
            return result
        except Exception as e:
            return {
                "insight_type": self._detect_insight_type(question),
                "title": "Analysis",
                "summary": f"Error generating insight: {str(e)}",
                "sql_queries": sql_queries,
                "key_findings": [],
                "recommendations": []
            }
