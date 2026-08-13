"""Groq-backed LLM services used by DataMind agents."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from typing import Protocol

from dotenv import load_dotenv


load_dotenv()

GROQ_SQL_MODEL = "llama-3.3-70b-versatile"


class SqlGenerationService(Protocol):
    """Dependency contract for services that turn a question into SQL."""

    def generate_sql(self, question: str, table_name: str, schema: Mapping[str, str]) -> str:
        """Generate one SQL query for the supplied dataset schema."""


class InsightGenerationService(Protocol):
    """Dependency contract for services that explain a completed SQL result."""

    def generate_insight(self, question: str, sql: str, columns: list[str], rows: list[dict[str, object]]) -> str:
        """Generate a concise answer grounded in the supplied query result."""


class IntentClassificationService(Protocol):
    """Dependency contract for classifying an Ask DataMind request."""

    def generate_intent(self, user_request: str) -> str:
        """Return the model's structured intent response."""


def extract_sql(response: str) -> str:
    """Return SQL from a plain or Markdown-fenced model response."""
    fenced = re.fullmatch(r"\s*```(?:sql)?\s*(.*?)\s*```\s*", response, re.IGNORECASE | re.DOTALL)
    return (fenced.group(1) if fenced else response).strip()


def build_sql_prompt(question: str, table_name: str, schema: Mapping[str, str]) -> str:
    """Build the SQL-only prompt sent to Groq with aggregation guidance."""
    schema_json = json.dumps(dict(schema), ensure_ascii=False)
    return f"""You are a SQL generation assistant for a data analytics application.

Generate exactly one SQLite-compatible SELECT query that answers the user's question.
Return only SQL, with no explanation and no Markdown fences.

Rules:
- Use only table {json.dumps(table_name)} and the supplied columns.
- Never invent tables or columns.
- Quote every table and column identifier with double quotes.
- Only read-only SELECT queries are allowed. Do not use INSERT, UPDATE, DELETE,
  DROP, ALTER, CREATE, ATTACH, DETACH, PRAGMA, or multiple statements.
- When a question asks which group has the highest, most, or total value of a
  measure (for example, "which region has the highest profit" or "highest
  sales by category"), aggregate the measure for every group with SUM(), use
  GROUP BY on the group column, then ORDER BY the SUM alias and LIMIT 1.
  Do not order individual rows for a group-level highest/most question.
- When a question asks how many records are in each group, use COUNT(*) and
  GROUP BY that group.

Example for a group-level highest measure question:
SELECT "dimension", SUM("measure") AS "total_measure"
FROM "table"
GROUP BY "dimension"
ORDER BY "total_measure" DESC
LIMIT 1

Table: {table_name}
Schema (column name to SQLite/Pandas type): {schema_json}
User question: {question}
"""


def build_insight_prompt(question: str, sql: str, columns: list[str], rows: list[dict[str, object]]) -> str:
    """Build the result-grounded prompt sent to Groq by the Insight Agent."""
    return f"""You are the Insight Agent for a data analytics application.

Answer the user's question concisely using only the authoritative SQL result below.
The SQL result is authoritative: do not invent values, perform unsupported
calculations, or claim information that is not present in it. Interpret the
result; do not replace the completed SQL or database computation. Format
numbers appropriately for a concise, useful answer. You may add up to three
brief observations only when they are directly supported by the result.
If the result is empty, say that no matching data was found.

User question: {question}
Executed SQL: {sql}
Result columns: {json.dumps(columns, ensure_ascii=False)}
Result rows: {json.dumps(rows, ensure_ascii=False, default=str)}
"""


def build_intent_prompt(user_request: str) -> str:
    """Build the constrained intent-classification prompt for Ask DataMind."""
    return f"""Classify this Ask DataMind request as either a data query or a dataset analysis request.

Return exactly one JSON object and no other text:
{{"intent": "query"}}
or:
{{"intent": "analysis"}}

Use "query" for requests for a value, comparison, count, aggregation, or answer from the dataset.
Use "analysis" for requests to analyze, summarize, or provide an overview of the dataset.

User request: {user_request}
"""


class GroqSqlService:
    """Generate SQLite SELECT statements from a question and dataset schema."""

    def __init__(self, api_key: str | None = None, model: str = GROQ_SQL_MODEL) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model

    def generate_sql(self, question: str, table_name: str, schema: Mapping[str, str]) -> str:
        """Ask Groq for SQL only; validation and execution remain local."""
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        # Import lazily so non-LLM backend commands continue to work until the
        # optional runtime dependency is installed from requirements.txt.
        from groq import Groq

        prompt = build_sql_prompt(question, table_name, schema)
        client = Groq(api_key=self.api_key)
        completion = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=512,
        )
        content = completion.choices[0].message.content
        if not content:
            raise ValueError("Groq did not return a SQL query.")
        return extract_sql(content)

    def generate_insight(self, question: str, sql: str, columns: list[str], rows: list[dict[str, object]]) -> str:
        """Ask Groq to explain an already-executed SQL result without computing it."""
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        from groq import Groq

        client = Groq(api_key=self.api_key)
        completion = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": build_insight_prompt(question, sql, columns, rows)}],
            temperature=0,
            max_tokens=256,
        )
        content = completion.choices[0].message.content
        if not content:
            raise ValueError("Groq did not return an insight.")
        return content.strip()

    def generate_intent(self, user_request: str) -> str:
        """Ask Groq for a constrained Ask DataMind intent classification."""
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        from groq import Groq

        client = Groq(api_key=self.api_key)
        completion = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": build_intent_prompt(user_request)}],
            temperature=0,
            max_tokens=32,
        )
        content = completion.choices[0].message.content
        if not content:
            raise ValueError("Groq did not return an intent.")
        return content.strip()
