"""
SQL Writer Agent v2 - Converts natural language to SQL queries
Enhanced with SQL Agent Toolset inspired by Uber FINCH
"""
from typing import Optional, Any
from dataclasses import dataclass
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from .tools import ColumnFinderTool, ValueFinderTool, TableRulesTool, ExecuteSQLTool


class SQLResult(BaseModel):
    """Generated SQL result"""
    intent: str = Field(description="The user's intent")
    assumptions: str = Field(description="Assumptions made")
    sql: str = Field(description="The generated SQL query")
    params: dict = Field(default_factory=dict, description="Query parameters")
    explanation: str = Field(description="Brief explanation of what the query does")
    
    # Keeping these for backward compatibility/internal use
    tables_used: list[str] = Field(default_factory=list, description="Tables referenced in query")
    confidence: float = Field(default=0.8, description="Confidence score 0-1")


class AgentContext(BaseModel):
    """Context built by tools during query processing - like FINCH diagram"""
    tables: list[dict] = Field(default_factory=list, description="Tables identified")
    columns: list[dict] = Field(default_factory=list, description="Columns found")
    values: list[dict] = Field(default_factory=list, description="Values resolved")
    rules: list[dict] = Field(default_factory=list, description="Table rules applied")


class SQLWriterAgent:
    """
    SQL Writer Agent v3 - Text-to-SQL with Toolset & Dialect Optimization
    
    Enhanced Features (from FINCH diagrams):
    - Column Finder Tool - Find columns by semantic meaning
    - Value Finder Tool - Resolve value aliases
    - Table Rules Tool - Get table constraints and examples
    - Execute SQL Tool - Safe query execution
    - Agent Context Building - Accumulate context from tools
    - Dialect Specific Optimization - Custom rules for SQLite, MySQL, Postgres, SQL Server
    """
    
    DIALECT_OPTIMIZATIONS = {
        "sqlite": """
- Use `LIMIT n` for top n results.
- Use `strftime('%Y-%m', date_col)` for date formatting.
- Use `random()` for random ordering.
- SQLite does NOT support `RIGHT JOIN` or `FULL OUTER JOIN` (use `LEFT JOIN`).
- Date manipulation: `date(col, '+1 day')`.
""",
        "mysql": """
- Use `LIMIT n` for top n results.
- Use `DATE_FORMAT(date_col, '%Y-%m')` for date formatting.
- Use `RAND()` for random ordering.
- Use backticks ` for identifiers if needed.
- String concatenation: `CONCAT(a, b)`.
""",
        "postgresql": """
- Use `LIMIT n` for top n results.
- Use `TO_CHAR(date_col, 'YYYY-MM')` for date formatting.
- Use `RANDOM()` for random ordering.
- Use `::` for type casting (e.g., `val::text`).
- ILIKE for case-insensitive matching.
""",
        "sqlserver": """
- Use `TOP n` for top n results (e.g., `SELECT TOP 10 * FROM ...`).
- Use `FORMAT(date_col, 'yyyy-MM')` for date formatting.
- Use `NEWID()` for random ordering.
- String concatenation: `+` or `CONCAT`.
- Use `[ ]` for identifiers if needed.
"""
    }
    
    SYSTEM_PROMPT = """You are an AI Agent specialized in converting natural language into SQL queries.

Your primary role:
- Understand user intent from natural language
- Map business concepts to database schema
- Generate safe, optimized, and correct SQL
- NEVER hallucinate tables, columns, or relationships
- NEVER guess schema — only use provided metadata

========================
DATABASE CONTEXT RULES
========================
- You will be given:
  1. Database dialect: {db_type}
  2. Schema metadata:
     {schema}
  3. Semantic Mappings (Business Terms → SQL):
     {semantic_mappings}
  4. Agent Context (from tools):
     {agent_context}

- Dialect Specific Optimization Rules:
{dialect_rules}

- You MUST use only these tables/columns
- If required data is missing → ask clarifying questions
- If mapping is ambiguous → ask user for clarification

========================
SECURITY RULES
========================
- NEVER generate:
  - DROP, DELETE, UPDATE, TRUNCATE, ALTER, INSERT
  - EXEC, CALL, stored procedures
  - DDL statements
- Only SELECT queries are allowed
- Always prevent SQL Injection:
  - Use parameterized placeholders when applicable
- No dynamic SQL
- No string concatenation logic

========================
QUERY QUALITY RULES
========================
- Prefer indexed columns in WHERE / JOIN
- Avoid SELECT *
- Always specify columns explicitly
- Use aliases for readability
- Use CTEs for complex logic
- Ensure deterministic ordering when using LIMIT
- Optimize joins (avoid cartesian joins)
- Avoid N+1 patterns

========================
LOGIC RULES
========================
- Handle:
  - Date ranges
  - Timezones
  - NULL values
  - Aggregations
  - Grouping
  - Window functions
  - Pagination
  - Ranking
  - Filtering
- Respect business logic semantics

========================
ERROR HANDLING
========================
If user request is:
- Impossible with current schema → respond:
  "Cannot generate SQL: missing required schema fields: {{{{fields}}}}"
- Ambiguous → ask clarification
- Unsafe → refuse politely

========================
OUTPUT FORMAT
========================
Always respond in JSON:

{{{{{{{{
  "intent": "...",
  "assumptions": "...",
  "sql": "...",
  "params": {{{{...}}}},
  "explanation": "..."
}}}}}}}}

{format_instructions}
"""

    EXAMPLE_TEMPLATE = ChatPromptTemplate.from_messages([
        ("human", "{question}"),
        ("ai", "{sql}")
    ])
    
    def __init__(self, llm, schema_manager=None, semantic_layer=None, 
                 vector_store=None, db_connector=None, db_type: str = "generic"):
        self.llm = llm
        self.schema_manager = schema_manager
        self.semantic_layer = semantic_layer
        self.vector_store = vector_store
        self.db_connector = db_connector
        self.db_type = db_type.lower()
        self.parser = PydanticOutputParser(pydantic_object=SQLResult)
        
        # Initialize tools
        self.column_finder = ColumnFinderTool(
            schema_manager=schema_manager,
            semantic_layer=semantic_layer
        )
        self.value_finder = ValueFinderTool(semantic_layer=semantic_layer)
        self.table_rules = TableRulesTool()
        self.execute_sql = ExecuteSQLTool(db_connector=db_connector)
        
        # Agent context accumulator
        self.context = AgentContext()
    
    def _extract_terms(self, question: str) -> list[str]:
        """Extract potential business terms from question"""
        # Simple word extraction - in production use NER
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'what', 'how',
                      'many', 'much', 'show', 'get', 'find', 'list', 'all', 'me',
                      'from', 'to', 'in', 'by', 'for', 'with', 'and', 'or', 'of'}
        
        words = question.lower().replace('?', '').replace(',', '').split()
        terms = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Also extract multi-word phrases
        if 'last month' in question.lower():
            terms.append('last month')
        if 'this year' in question.lower():
            terms.append('this year')
        if 'order date' in question.lower():
            terms.append('order date')
            
        return terms
    
    async def _build_context(self, question: str) -> AgentContext:
        """Build agent context using tools - like FINCH diagram 2"""
        context = AgentContext()
        terms = self._extract_terms(question)
        tables_found = set()
        
        # Use Column Finder for each term
        for term in terms:
            columns = self.column_finder._run(term)
            for col in columns:
                if col not in context.columns:
                    context.columns.append(col)
                    tables_found.add(col.get('table', ''))
        
        # Use Value Finder for potential value aliases
        for term in terms:
            value_result = self.value_finder._run(term)
            if value_result.get('found'):
                context.values.append(value_result)
        
        # Get rules for identified tables
        for table in tables_found:
            if table and table != '*':
                rules = self.table_rules._run(table)
                context.rules.append(rules)
                context.tables.append({"name": table, "description": rules.get("description", "")})
        
        return context
    
    def _format_context(self, context: AgentContext) -> str:
        """Format agent context for prompt"""
        lines = []
        
        if context.tables:
            lines.append("### Identified Tables:")
            for t in context.tables[:5]:
                lines.append(f"  - {t.get('name')}: {t.get('description', '')}")
        
        if context.columns:
            lines.append("\n### Resolved Columns:")
            for c in context.columns[:8]:
                lines.append(f"  - {c.get('table')}.{c.get('column')} ({c.get('data_type')})")
        
        if context.values:
            lines.append("\n### Resolved Values:")
            for v in context.values[:5]:
                vals = ', '.join(str(x) for x in v.get('values', []))
                lines.append(f"  - \"{v.get('alias')}\" → {vals}")
        
        if context.rules:
            lines.append("\n### Example Queries:")
            for r in context.rules[:3]:
                for ex in r.get('example_queries', [])[:2]:
                    lines.append(f"  Q: {ex.get('question')}")
                    lines.append(f"  A: {ex.get('sql')}")
        
        return "\n".join(lines) if lines else "No additional context"
    
    def _get_few_shot_examples(self, question: str, k: int = 3) -> list[dict]:
        """Retrieve similar SQL examples from vector store"""
        if not self.vector_store:
            return self._get_default_examples()
        
        examples = self.vector_store.search_similar(question, k=k)
        return examples if examples else self._get_default_examples()
    
    def _get_default_examples(self) -> list[dict]:
        """Default SQL examples for few-shot learning"""
        return [
            {
                "question": "Show all customers", 
                "sql": "SELECT id, name, email, created_at FROM customers LIMIT 100"
            },
            {
                "question": "Total revenue by month", 
                "sql": """
WITH MonthlySales AS (
    SELECT 
        strftime('%Y-%m', order_date) as sales_month, 
        SUM(total_amount) as revenue 
    FROM orders 
    GROUP BY 1
)
SELECT sales_month, revenue 
FROM MonthlySales 
ORDER BY sales_month DESC
LIMIT 12;
"""
            },
            {
                "question": "Top 10 products by sales", 
                "sql": """
SELECT 
    p.name, 
    COALESCE(SUM(oi.quantity), 0) as total_sold 
FROM products p 
JOIN order_items oi ON p.id = oi.product_id 
GROUP BY p.id, p.name 
ORDER BY total_sold DESC 
LIMIT 10;
"""
            }
        ]
    
    def _get_schema_info(self) -> str:
        """Get database schema information"""
        if self.schema_manager:
            return self.schema_manager.get_schema_description()
        return "Schema not available"
    
    def _get_semantic_mappings(self) -> str:
        """Get semantic layer mappings"""
        if self.semantic_layer:
            return self.semantic_layer.get_mappings_description()
        return "No custom mappings defined"
    
    def _build_prompt(self, question: str) -> ChatPromptTemplate:
        """Build the prompt with few-shot examples and dialect optimizations"""
        examples = self._get_few_shot_examples(question)
        
        # Get dialect-specific rules
        dialect_rules = self.DIALECT_OPTIMIZATIONS.get(self.db_type, "No specific dialect rules.")
        
        # Inject dialect rules into system prompt
        system_prompt = self.SYSTEM_PROMPT.format(
            db_type=self.db_type,
            schema="{schema}",
            semantic_mappings="{semantic_mappings}",
            agent_context="{agent_context}",
            format_instructions="{format_instructions}",
            dialect_rules=dialect_rules
        )
        
        few_shot_prompt = FewShotChatMessagePromptTemplate(
            example_prompt=self.EXAMPLE_TEMPLATE,
            examples=examples
        )
        
        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            few_shot_prompt,
            ("human", "Convert this question to SQL: {question}")
        ])
    
    async def generate_sql(self, question: str) -> SQLResult:
        """Generate SQL from natural language question with tool-assisted context"""
        # Build context using tools
        context = await self._build_context(question)
        self.context = context  # Store for inspection
        
        prompt = self._build_prompt(question)
        chain = prompt | self.llm | self.parser
        
        try:
            result = await chain.ainvoke({
                "question": question,
                "schema": self._get_schema_info(),
                "semantic_mappings": self._get_semantic_mappings(),
                "agent_context": self._format_context(context),
                "format_instructions": self.parser.get_format_instructions()
            })
            return result
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            error_sql = f"/*\nERROR GENERATING SQL:\n{str(e)}\n\nTRACEBACK:\n{tb}\n*/"
            
            return SQLResult(
                intent="Error",
                assumptions="None",
                sql=error_sql,
                explanation=f"Error generating SQL. Check the SQL console for technical details.",
                confidence=0.0
            )
    
    async def generate_and_execute(self, question: str) -> dict:
        """Generate SQL and execute it - full pipeline"""
        sql_result = await self.generate_sql(question)
        
        if not sql_result.sql:
            return {
                "success": False,
                "error": sql_result.explanation,
                "sql": "",
                "data": None
            }
        
        # Execute using tool
        exec_result = await self.execute_sql._arun(sql_result.sql)
        
        return {
            "success": exec_result.get("success", False),
            "question": question,
            "sql": sql_result.sql,
            "explanation": sql_result.explanation,
            "context": self.context.model_dump(),
            "data": exec_result if exec_result.get("success") else None,
            "error": exec_result.get("error") if not exec_result.get("success") else None
        }
    
    def generate_sql_sync(self, question: str) -> SQLResult:
        """Synchronous version of generate_sql"""
        import asyncio
        return asyncio.run(self.generate_sql(question))
