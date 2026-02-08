"""
Report Agent - Generate Predefined Reports
Inspired by Uber FINCH's Report Generation intent
"""
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field


class ReportResult(BaseModel):
    """Report generation result"""
    report_name: str = Field(description="Name of the report")
    report_type: str = Field(description="Type: summary, detail, comparison")
    sql_queries: list[str] = Field(description="SQL queries to generate report")
    explanation: str = Field(description="What this report shows")
    format_template: Optional[str] = Field(default=None, description="Output format template")


@dataclass
class ReportTemplate:
    """Predefined report template"""
    name: str
    description: str
    sql_template: str
    parameters: list[str] = field(default_factory=list)
    output_columns: list[str] = field(default_factory=list)


class ReportAgent:
    """
    Report Agent - Predefined Report Generation
    
    Features (inspired by FINCH):
    - P&L Report generation
    - Sales Summary reports
    - Inventory reports
    - Custom report templates
    - Parameter substitution
    - Scheduled report support
    
    Sub-intents handled:
    - PO Activity Report
    - P&L Report
    - Sales Summary
    - Custom reports
    """
    
    SYSTEM_PROMPT = """You are a Report Generator Agent specializing in business reports.

Given a report request, you should:
1. Identify which predefined report matches the request
2. Generate the SQL queries needed
3. Specify the output format

Available Report Templates:
{templates}

User Request: {request}

Generate the report configuration in JSON format:
{format_instructions}
"""
    
    # Predefined report templates
    TEMPLATES = {
        "sales_summary": ReportTemplate(
            name="Sales Summary",
            description="Daily/Weekly/Monthly sales overview",
            sql_template="""
                SELECT 
                    {period} as period,
                    COUNT(*) as total_orders,
                    SUM(total_amount) as revenue,
                    AVG(total_amount) as avg_order_value
                FROM orders
                WHERE order_date >= {start_date} AND order_date < {end_date}
                GROUP BY {period}
                ORDER BY period
            """,
            parameters=["period", "start_date", "end_date"],
            output_columns=["period", "total_orders", "revenue", "avg_order_value"]
        ),
        "customer_report": ReportTemplate(
            name="Customer Report",
            description="Customer analysis and segmentation",
            sql_template="""
                SELECT 
                    c.id, c.name, c.email, c.city,
                    COUNT(o.id) as order_count,
                    SUM(o.total_amount) as total_spent,
                    MAX(o.order_date) as last_order
                FROM customers c
                LEFT JOIN orders o ON c.id = o.customer_id
                GROUP BY c.id, c.name, c.email, c.city
                ORDER BY total_spent DESC
                LIMIT {limit}
            """,
            parameters=["limit"],
            output_columns=["id", "name", "email", "city", "order_count", "total_spent", "last_order"]
        ),
        "product_performance": ReportTemplate(
            name="Product Performance",
            description="Top performing products",
            sql_template="""
                SELECT 
                    p.name as product,
                    p.category,
                    SUM(oi.quantity) as units_sold,
                    SUM(oi.quantity * oi.unit_price) as revenue
                FROM products p
                JOIN order_items oi ON p.id = oi.product_id
                JOIN orders o ON oi.order_id = o.id
                WHERE o.order_date >= {start_date}
                GROUP BY p.id, p.name, p.category
                ORDER BY revenue DESC
                LIMIT {limit}
            """,
            parameters=["start_date", "limit"],
            output_columns=["product", "category", "units_sold", "revenue"]
        ),
        "inventory_status": ReportTemplate(
            name="Inventory Status",
            description="Current inventory levels and reorder alerts",
            sql_template="""
                SELECT 
                    p.name,
                    p.category,
                    p.stock_quantity,
                    p.reorder_level,
                    CASE WHEN p.stock_quantity < p.reorder_level 
                         THEN 'REORDER' ELSE 'OK' END as status
                FROM products p
                ORDER BY status DESC, stock_quantity ASC
            """,
            parameters=[],
            output_columns=["name", "category", "stock_quantity", "reorder_level", "status"]
        ),
        "revenue_by_region": ReportTemplate(
            name="Revenue by Region",
            description="Geographic revenue breakdown",
            sql_template="""
                SELECT 
                    c.city as region,
                    COUNT(DISTINCT c.id) as customers,
                    COUNT(o.id) as orders,
                    SUM(o.total_amount) as revenue
                FROM customers c
                JOIN orders o ON c.id = o.customer_id
                WHERE o.order_date >= {start_date}
                GROUP BY c.city
                ORDER BY revenue DESC
            """,
            parameters=["start_date"],
            output_columns=["region", "customers", "orders", "revenue"]
        )
    }
    
    def __init__(self, llm=None):
        self.llm = llm
        self.parser = JsonOutputParser(pydantic_object=ReportResult)
    
    def _get_template_descriptions(self) -> str:
        """Format templates for prompt"""
        lines = []
        for key, template in self.TEMPLATES.items():
            params = ", ".join(template.parameters) if template.parameters else "none"
            lines.append(f"- **{template.name}** ({key}): {template.description} [params: {params}]")
        return "\n".join(lines)
    
    async def generate_report(
        self,
        request: str,
        parameters: Optional[dict] = None
    ) -> dict:
        """Generate report based on request"""
        parameters = parameters or {}
        
        # Try to match predefined template
        matched_template = self._match_template(request)
        
        if matched_template:
            return self._generate_from_template(matched_template, parameters)
        
        # Use LLM for custom report
        if self.llm:
            return await self._generate_custom_report(request, parameters)
        
        return {
            "error": "No matching template and LLM not configured",
            "available_templates": list(self.TEMPLATES.keys())
        }
    
    def _match_template(self, request: str) -> Optional[ReportTemplate]:
        """Match request to predefined template"""
        request_lower = request.lower()
        
        keywords = {
            "sales_summary": ["sales", "bán hàng", "doanh số", "revenue summary"],
            "customer_report": ["customer", "khách hàng", "client"],
            "product_performance": ["product", "sản phẩm", "top product", "best selling"],
            "inventory_status": ["inventory", "tồn kho", "stock", "kho"],
            "revenue_by_region": ["region", "vùng", "khu vực", "city", "thành phố"]
        }
        
        for template_key, kws in keywords.items():
            if any(kw in request_lower for kw in kws):
                return self.TEMPLATES[template_key]
        
        return None
    
    def _generate_from_template(
        self,
        template: ReportTemplate,
        parameters: dict
    ) -> dict:
        """Generate report from template"""
        # Fill in default parameters
        defaults = {
            "period": "strftime('%Y-%m', order_date)",
            "start_date": "date('now', '-30 days')",
            "end_date": "date('now')",
            "limit": "20"
        }
        
        params = {**defaults, **parameters}
        
        # Substitute parameters in SQL
        sql = template.sql_template
        for param, value in params.items():
            sql = sql.replace(f"{{{param}}}", str(value))
        
        return {
            "report_name": template.name,
            "report_type": "predefined",
            "sql_queries": [sql.strip()],
            "explanation": template.description,
            "output_columns": template.output_columns,
            "parameters_used": params
        }
    
    async def _generate_custom_report(
        self,
        request: str,
        parameters: dict
    ) -> dict:
        """Generate custom report using LLM"""
        prompt = ChatPromptTemplate.from_template(self.SYSTEM_PROMPT)
        
        chain = prompt | self.llm | self.parser
        
        try:
            result = await chain.ainvoke({
                "templates": self._get_template_descriptions(),
                "request": request,
                "format_instructions": self.parser.get_format_instructions()
            })
            return result
        except Exception as e:
            return {"error": str(e)}
    
    def list_templates(self) -> list[dict]:
        """List available report templates"""
        return [
            {
                "key": key,
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters
            }
            for key, t in self.TEMPLATES.items()
        ]
