"""Structured results produced by the SQL Agent."""

from typing import Any

from pydantic import BaseModel


class SqlResult(BaseModel):
    question: str
    sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
