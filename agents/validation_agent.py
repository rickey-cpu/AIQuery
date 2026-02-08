"""
Validation Agent - Validates SQL queries before execution
"""
import re
from typing import Optional
from dataclasses import dataclass
from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    """SQL validation result"""
    is_valid: bool = Field(description="Whether the SQL is valid and safe")
    sql: str = Field(description="The validated/cleaned SQL")
    errors: list[str] = Field(default_factory=list, description="List of validation errors")
    warnings: list[str] = Field(default_factory=list, description="List of warnings")
    estimated_cost: str = Field(default="low", description="Estimated query cost: low, medium, high")


class ValidationAgent:
    """
    Validation Agent - Ensures SQL safety and correctness
    
    Responsibilities:
    - Syntax validation
    - Security checks (prevent SQL injection, destructive queries)
    - Performance estimation
    - Query optimization suggestions
    """
    
    # Dangerous patterns to block
    BLOCKED_PATTERNS = [
        r'\bDROP\b',
        r'\bDELETE\b',
        r'\bTRUNCATE\b',
        r'\bALTER\b',
        r'\bCREATE\b',
        r'\bINSERT\b',
        r'\bUPDATE\b',
        r'\bGRANT\b',
        r'\bREVOKE\b',
        r';\s*--',  # SQL injection pattern
        r'\bEXEC\b',
        r'\bEXECUTE\b',
    ]
    
    # Warning patterns
    WARNING_PATTERNS = [
        (r'SELECT\s+\*', "Using SELECT * - consider specifying columns"),
        (r'(?<!LIMIT\s)\d{4,}', "Large number detected - verify if intentional"),
        (r'\bJOIN\b.*\bJOIN\b.*\bJOIN\b', "Multiple JOINs detected - may be slow"),
    ]
    
    def __init__(self):
        self.blocked_patterns = [re.compile(p, re.IGNORECASE) for p in self.BLOCKED_PATTERNS]
        self.warning_patterns = [(re.compile(p, re.IGNORECASE), msg) for p, msg in self.WARNING_PATTERNS]
    
    def validate(self, sql: str) -> ValidationResult:
        """Validate SQL query"""
        errors = []
        warnings = []
        
        # Check for empty SQL
        if not sql or not sql.strip():
            return ValidationResult(
                is_valid=False,
                sql="",
                errors=["Empty SQL query"]
            )
        
        # Clean the SQL
        cleaned_sql = self._clean_sql(sql)
        
        # Check for blocked patterns
        for pattern in self.blocked_patterns:
            if pattern.search(cleaned_sql):
                errors.append(f"Blocked operation detected: {pattern.pattern}")
        
        # Check for warnings
        for pattern, message in self.warning_patterns:
            if pattern.search(cleaned_sql):
                warnings.append(message)
        
        # Must be a SELECT query
        if not cleaned_sql.strip().upper().startswith('SELECT'):
            errors.append("Only SELECT queries are allowed")
        
        # Estimate cost
        estimated_cost = self._estimate_cost(cleaned_sql)
        
        # Add LIMIT if not present and no aggregation
        if not re.search(r'\bLIMIT\b', cleaned_sql, re.IGNORECASE):
            if not re.search(r'\b(COUNT|SUM|AVG|MAX|MIN)\s*\(', cleaned_sql, re.IGNORECASE):
                if not re.search(r'\bGROUP\s+BY\b', cleaned_sql, re.IGNORECASE):
                    cleaned_sql = cleaned_sql.rstrip(';') + ' LIMIT 1000'
                    warnings.append("Added LIMIT 1000 to prevent large result sets")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            sql=cleaned_sql,
            errors=errors,
            warnings=warnings,
            estimated_cost=estimated_cost
        )
    
    def _clean_sql(self, sql: str) -> str:
        """Clean and normalize SQL"""
        # Remove comments
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        
        # Normalize whitespace
        sql = ' '.join(sql.split())
        
        # Remove trailing semicolons (we'll add one at execution)
        sql = sql.rstrip(';')
        
        return sql.strip()
    
    def _estimate_cost(self, sql: str) -> str:
        """Estimate query cost based on patterns"""
        sql_upper = sql.upper()
        
        # High cost indicators
        high_cost_patterns = [
            r'SELECT\s+\*.*JOIN.*JOIN.*JOIN',  # SELECT * with multiple joins
            r'NOT\s+IN\s*\(',  # NOT IN subquery
            r'LIKE\s+[\'"]%',  # Leading wildcard
        ]
        
        # Medium cost indicators
        medium_cost_patterns = [
            r'JOIN',
            r'GROUP\s+BY',
            r'ORDER\s+BY',
            r'DISTINCT',
        ]
        
        for pattern in high_cost_patterns:
            if re.search(pattern, sql_upper):
                return "high"
        
        for pattern in medium_cost_patterns:
            if re.search(pattern, sql_upper):
                return "medium"
        
        return "low"
