import re
import logging
from typing import Any

import llm
import database
import prompt as prompt_templates

logger = logging.getLogger("sql_assistant.agent")

FORBIDDEN_KEYWORDS = [
    "DELETE", "DROP", "UPDATE", "INSERT", "ALTER", "CREATE",
    "TRUNCATE", "REPLACE", "ATTACH", "DETACH", "VACUUM",
]

SAFE_KEYWORDS = ["SELECT", "WITH", "EXPLAIN", "PRAGMA"]


def validate_sql(sql: str) -> tuple[bool, str]:
    cleaned = sql.strip().strip(";").strip()
    upper = cleaned.upper()

    if not any(cleaned.upper().startswith(k) for k in SAFE_KEYWORDS):
        return False, "Only SELECT queries are allowed."

    for kw in FORBIDDEN_KEYWORDS:
        pattern = r'\b' + kw + r'\b'
        if re.search(pattern, upper):
            return False, f"Query contains forbidden keyword: {kw}"

    return True, ""


async def generate_sql(question: str, history: list[dict] | None = None) -> str:
    schema = database.get_schema_text()
    history_text = ""
    if history:
        lines = []
        for h in history[-5:]:
            lines.append(f"Q: {h.get('question', '')}")
            lines.append(f"A: {h.get('sql', '')}")
        history_text = "\n".join(lines)

    system = prompt_templates.SYSTEM_PROMPT.format(
        schema=schema, history=history_text
    )
    sql = await llm.generate(question, system=system, temperature=0.05)

    sql = sql.strip()
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[-1]
        sql = sql.rsplit("```", 1)[0]
    sql = sql.strip()

    valid, error = validate_sql(sql)
    if not valid:
        raise ValueError(f"SQL validation failed: {error}")

    logger.info(f"Generated SQL: {sql}")
    return sql


async def explain_results(
    question: str, sql: str, columns: list[str], rows: list[list[Any]]
) -> str:
    sample = rows[:5]
    sample_data = "\n".join(
        ", ".join(str(v) for v in row) for row in sample
    )
    prompt = prompt_templates.EXPLAIN_PROMPT.format(
        question=question,
        sql=sql,
        row_count=len(rows),
        columns=", ".join(columns),
        sample_rows=min(5, len(rows)),
        sample_data=sample_data,
    )
    return await llm.generate(prompt, temperature=0.2)


def detect_chart_type(columns: list[str], rows: list[list[Any]]) -> dict[str, Any] | None:
    if len(rows) < 2:
        return None

    numeric_cols = []
    label_cols = []

    for i, col in enumerate(columns):
        numeric = True
        for row in rows[:20]:
            if row[i] is not None:
                try:
                    float(row[i])
                except (ValueError, TypeError):
                    numeric = False
                    break
        if numeric:
            numeric_cols.append(i)
        else:
            label_cols.append(i)

    if not numeric_cols or not label_cols:
        return None

    label_idx = label_cols[0]
    value_idx = numeric_cols[0]

    labels = [str(row[label_idx]) for row in rows[:20]]
    values = [float(row[value_idx]) for row in rows[:20]]

    unique_labels = len(set(labels))
    if unique_labels <= 6:
        chart_type = "pie"
    elif unique_labels <= 20:
        chart_type = "bar"
    else:
        chart_type = "line"

    return {
        "chart_type": chart_type,
        "label_column": columns[label_idx],
        "value_column": columns[value_idx],
        "title": f"{columns[value_idx]} by {columns[label_idx]}",
        "labels": labels,
        "values": values,
    }


async def generate_sample_questions() -> list[str]:
    schema = database.get_schema_text()
    prompt = prompt_templates.SAMPLE_QUESTIONS_PROMPT.format(schema=schema)
    content = await llm.generate(prompt, temperature=0.3)
    questions = []
    for line in content.strip().split("\n"):
        line = line.strip()
        if line and (line[0].isdigit() or line.startswith("-")):
            cleaned = re.sub(r"^[\d\.\-\s\)]+", "", line).strip()
            if cleaned:
                questions.append(cleaned)
    return questions[:5]
