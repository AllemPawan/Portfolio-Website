import os
import csv
import io
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles

import database
import sql_agent
import llm as llm_module
from models import (
    QueryRequest, QueryResponse, SchemaInfo, TableInfo,
    UploadResponse, HealthResponse, HistoryItem,
)
from utils import setup_logging, timeit

setup_logging()
logger = logging.getLogger("sql_assistant.api")

app = FastAPI(title="SQL AI Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files as fallback
_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")

history: list[dict[str, Any]] = []
current_db_name: str | None = None


@app.get("/api/health", response_model=HealthResponse)
async def health():
    ollama_ok = await llm_module.check_health()
    db_ok = database.get_db_path() is not None
    return HealthResponse(
        status="ok",
        ollama="connected" if ollama_ok else "disconnected",
        database=f"loaded: {current_db_name}" if db_ok else "none",
    )


@app.post("/api/upload-db", response_model=UploadResponse)
async def upload_db(file: UploadFile = File(...)):
    global current_db_name

    if not file.filename or not file.filename.endswith(".db"):
        raise HTTPException(400, "Only .db files are supported")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(400, "Empty file")

    current_db_name = file.filename
    database.save_uploaded_db(content, file.filename)
    tables = database.get_tables_summary()
    table_names = [t["name"] for t in tables]

    logger.info(f"Database uploaded: {file.filename} with tables: {table_names}")
    return UploadResponse(
        message=f"Database '{file.filename}' uploaded successfully",
        database=file.filename,
        tables=table_names,
    )


@app.get("/api/schema")
async def get_schema() -> SchemaInfo:
    if not database.get_db_path():
        raise HTTPException(400, "No database uploaded")
    tables = database.get_schema()
    return SchemaInfo(tables=tables)


@app.get("/api/tables")
async def get_tables() -> list[TableInfo]:
    if not database.get_db_path():
        raise HTTPException(400, "No database uploaded")
    tables = database.get_tables_summary()
    return [
        TableInfo(
            name=t["name"],
            row_count=t["row_count"],
            columns=t["columns"],
        )
        for t in tables
    ]


@app.post("/api/query", response_model=QueryResponse)
@timeit
async def query(req: QueryRequest):
    if not database.get_db_path():
        raise HTTPException(400, "No database uploaded. Upload a database first.")

    question = req.question.strip()
    if not question:
        raise HTTPException(400, "Question cannot be empty")

    try:
        sql = await sql_agent.generate_sql(question, history)
    except ValueError as e:
        raise HTTPException(400, str(e))

    columns, rows, elapsed = database.execute_query(sql)

    explanation = await sql_agent.explain_results(question, sql, columns, rows)

    chart = sql_agent.detect_chart_type(columns, rows)

    history.append({
        "question": question,
        "sql": sql,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return QueryResponse(
        question=question,
        sql=sql,
        sql_explanation="",
        execution_time_ms=round(elapsed, 2),
        row_count=len(rows),
        columns=columns,
        rows=rows[:500],
        explanation=explanation,
        chart_type=chart["chart_type"] if chart else None,
        chart_data=chart if chart else None,
    )


@app.get("/api/history")
async def get_history() -> list[HistoryItem]:
    return [
        HistoryItem(
            question=h["question"],
            sql=h["sql"],
            timestamp=h["timestamp"],
        )
        for h in history[-50:]
    ]


@app.get("/api/export/{fmt}")
async def export(fmt: str, sql: str = Query(default=""), question: str = Query(default="")):
    if fmt not in ("csv", "json", "sql"):
        raise HTTPException(400, "Format must be csv, json, or sql")

    if question:
        try:
            sql = await sql_agent.generate_sql(question, history)
        except ValueError as e:
            raise HTTPException(400, str(e))

    if not sql:
        raise HTTPException(400, "No SQL provided and no valid question to generate from")

    columns, rows, _ = database.execute_query(sql)

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(rows)
        content = output.getvalue()
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=export.csv"},
        )
    elif fmt == "json":
        data = [dict(zip(columns, row)) for row in rows]
        return Response(
            content=json.dumps(data, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=export.json"},
        )
    elif fmt == "sql":
        content = f"-- Generated SQL\n-- {datetime.now().isoformat()}\n\n{sql};\n"
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=export.sql"},
        )


@app.get("/api/sample-questions")
async def sample_questions():
    if not database.get_db_path():
        raise HTTPException(400, "No database uploaded")
    questions = await sql_agent.generate_sample_questions()
    return {"questions": questions}


@app.get("/api/clear-history")
async def clear_history():
    history.clear()
    return {"message": "History cleared"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
