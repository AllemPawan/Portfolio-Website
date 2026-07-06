from pydantic import BaseModel, Field
from typing import Any, Optional


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class QueryResponse(BaseModel):
    question: str
    sql: str
    sql_explanation: str
    execution_time_ms: float
    row_count: int
    columns: list[str]
    rows: list[list[Any]]
    explanation: str
    chart_type: Optional[str] = None
    chart_data: Optional[dict[str, Any]] = None


class SchemaInfo(BaseModel):
    tables: list[dict[str, Any]]


class TableInfo(BaseModel):
    name: str
    row_count: int
    columns: list[dict[str, str]]


class UploadResponse(BaseModel):
    message: str
    database: str
    tables: list[str]


class ExportResponse(BaseModel):
    filename: str
    content: str
    content_type: str


class HistoryItem(BaseModel):
    question: str
    sql: str
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    ollama: str
    database: str
