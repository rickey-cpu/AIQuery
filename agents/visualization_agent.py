"""
Visualization Agent - Generate Charts and Dashboards
Adds visual output capabilities like enterprise BI tools
"""
from typing import Optional, Any
from dataclasses import dataclass
from enum import Enum


class ChartType(Enum):
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    TABLE = "table"
    METRIC = "metric"  # Single KPI


@dataclass
class ChartConfig:
    """Chart configuration for frontend"""
    chart_type: ChartType
    title: str
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    series: list[str] = None
    colors: list[str] = None
    options: dict = None
    
    def to_dict(self) -> dict:
        return {
            "type": self.chart_type.value,
            "title": self.title,
            "xAxis": self.x_axis,
            "yAxis": self.y_axis,
            "series": self.series or [],
            "colors": self.colors or [],
            "options": self.options or {}
        }


class VisualizationAgent:
    """
    Visualization Agent - Chart Generation
    
    Features:
    - Auto-select chart type based on data
    - Generate Chart.js / ECharts config
    - Dashboard composition
    - Responsive design hints
    
    Supported outputs:
    - Bar charts (comparisons)
    - Line charts (trends)
    - Pie charts (proportions)
    - Area charts (cumulative)
    - Tables (detail data)
    - KPI cards (single metrics)
    """
    
    # Default color palette
    COLORS = [
        "#3B82F6",  # Blue
        "#10B981",  # Green
        "#F59E0B",  # Amber
        "#EF4444",  # Red
        "#8B5CF6",  # Purple
        "#EC4899",  # Pink
        "#06B6D4",  # Cyan
        "#84CC16",  # Lime
    ]
    
    def __init__(self):
        pass
    
    def auto_select_chart(self, data: dict, context: Optional[dict] = None) -> ChartType:
        """Automatically select best chart type for data"""
        columns = data.get("columns", [])
        rows = data.get("rows", [])
        
        if not rows:
            return ChartType.TABLE
        
        row_count = len(rows)
        col_count = len(columns)
        
        # Single value = Metric card
        if row_count == 1 and col_count == 1:
            return ChartType.METRIC
        
        # Single row with multiple columns = Metric or table
        if row_count == 1:
            return ChartType.METRIC
        
        # Check column types
        has_time = any("date" in c.lower() or "month" in c.lower() or "year" in c.lower() 
                       for c in columns)
        has_category = any("name" in c.lower() or "city" in c.lower() or "category" in c.lower()
                          for c in columns)
        has_numeric = any("sum" in c.lower() or "count" in c.lower() or "total" in c.lower() or
                         "revenue" in c.lower() or "amount" in c.lower()
                         for c in columns)
        
        # Time series = Line chart
        if has_time and has_numeric:
            return ChartType.LINE
        
        # Few categories with values = Bar chart
        if has_category and has_numeric and row_count <= 10:
            return ChartType.BAR
        
        # Proportions (few rows) = Pie chart
        if row_count <= 5 and col_count == 2:
            return ChartType.PIE
        
        # Many rows = Table
        if row_count > 20:
            return ChartType.TABLE
        
        # Default to bar for comparisons
        return ChartType.BAR
    
    def generate_chart_config(
        self,
        data: dict,
        chart_type: Optional[ChartType] = None,
        title: str = "Query Result"
    ) -> ChartConfig:
        """Generate chart configuration"""
        columns = data.get("columns", [])
        rows = data.get("rows", [])
        
        if chart_type is None:
            chart_type = self.auto_select_chart(data)
        
        if chart_type == ChartType.METRIC:
            return self._metric_config(data, title)
        elif chart_type == ChartType.LINE:
            return self._line_config(data, title)
        elif chart_type == ChartType.BAR:
            return self._bar_config(data, title)
        elif chart_type == ChartType.PIE:
            return self._pie_config(data, title)
        else:
            return self._table_config(data, title)
    
    def _metric_config(self, data: dict, title: str) -> ChartConfig:
        """Generate metric/KPI config"""
        columns = data.get("columns", [])
        rows = data.get("rows", [])
        
        value = rows[0][0] if rows else 0
        label = columns[0] if columns else "Value"
        
        return ChartConfig(
            chart_type=ChartType.METRIC,
            title=title,
            options={
                "value": value,
                "label": label,
                "format": self._detect_format(value)
            }
        )
    
    def _line_config(self, data: dict, title: str) -> ChartConfig:
        """Generate line chart config"""
        columns = data.get("columns", [])
        rows = data.get("rows", [])
        
        # First column as X axis, rest as series
        x_axis = columns[0]
        series = columns[1:] if len(columns) > 1 else []
        
        return ChartConfig(
            chart_type=ChartType.LINE,
            title=title,
            x_axis=x_axis,
            y_axis="Value",
            series=series,
            colors=self.COLORS[:len(series)],
            options={
                "data": self._format_for_chartjs(data),
                "smooth": True
            }
        )
    
    def _bar_config(self, data: dict, title: str) -> ChartConfig:
        """Generate bar chart config"""
        columns = data.get("columns", [])
        rows = data.get("rows", [])
        
        x_axis = columns[0]
        series = columns[1:] if len(columns) > 1 else []
        
        return ChartConfig(
            chart_type=ChartType.BAR,
            title=title,
            x_axis=x_axis,
            y_axis="Value",
            series=series,
            colors=self.COLORS[:len(series)],
            options={
                "data": self._format_for_chartjs(data),
                "horizontal": len(rows) > 8
            }
        )
    
    def _pie_config(self, data: dict, title: str) -> ChartConfig:
        """Generate pie chart config"""
        columns = data.get("columns", [])
        rows = data.get("rows", [])
        
        return ChartConfig(
            chart_type=ChartType.PIE,
            title=title,
            series=[columns[0]] if columns else [],
            colors=self.COLORS[:len(rows)],
            options={
                "data": [
                    {"name": str(row[0]), "value": row[1] if len(row) > 1 else 0}
                    for row in rows
                ],
                "donut": True
            }
        )
    
    def _table_config(self, data: dict, title: str) -> ChartConfig:
        """Generate table config"""
        return ChartConfig(
            chart_type=ChartType.TABLE,
            title=title,
            options={
                "columns": data.get("columns", []),
                "rows": data.get("rows", []),
                "pagination": len(data.get("rows", [])) > 10
            }
        )
    
    def _format_for_chartjs(self, data: dict) -> dict:
        """Format data for Chart.js"""
        columns = data.get("columns", [])
        rows = data.get("rows", [])
        
        if not rows:
            return {"labels": [], "datasets": []}
        
        labels = [str(row[0]) for row in rows]
        datasets = []
        
        for i, col in enumerate(columns[1:], 1):
            datasets.append({
                "label": col,
                "data": [row[i] if i < len(row) else 0 for row in rows],
                "backgroundColor": self.COLORS[i - 1] if i <= len(self.COLORS) else self.COLORS[0]
            })
        
        return {
            "labels": labels,
            "datasets": datasets
        }
    
    def _detect_format(self, value) -> str:
        """Detect value format for display"""
        if isinstance(value, float):
            if value > 1000000:
                return "compact"  # 1.2M
            elif value < 1:
                return "percent"
            else:
                return "decimal"
        elif isinstance(value, int):
            if value > 1000000:
                return "compact"
            return "number"
        return "text"
    
    def generate_dashboard(
        self,
        queries_data: list[dict],
        layout: str = "grid"
    ) -> dict:
        """Generate dashboard from multiple queries"""
        charts = []
        
        for i, qd in enumerate(queries_data):
            data = qd.get("data", {})
            title = qd.get("title", f"Chart {i + 1}")
            chart_type = qd.get("chart_type")
            
            if chart_type:
                chart_type = ChartType(chart_type)
            
            config = self.generate_chart_config(data, chart_type, title)
            charts.append(config.to_dict())
        
        return {
            "layout": layout,
            "charts": charts,
            "responsive": True
        }
