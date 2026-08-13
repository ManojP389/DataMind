"""Safe SQLite utilities for querying uploaded CSV datasets."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from app.tools.data_tools import read_csv_with_fallback_encodings


FORBIDDEN_SQL = re.compile(r"\b(?:INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|ATTACH|DETACH|PRAGMA|REPLACE|VACUUM)\b", re.IGNORECASE)
IDENTIFIER = re.compile(r"^.+$", re.DOTALL)
DATASET_TABLE_NAME = "dataset"


def quote_identifier(identifier: str) -> str:
    """Quote a CSV-derived SQLite identifier, including names with punctuation."""
    if not IDENTIFIER.fullmatch(identifier):
        raise ValueError("Unsupported dataset column name.")
    return f'"{identifier.replace(chr(34), chr(34) * 2)}"'


def validate_select_query(sql: str) -> str:
    """Allow one read-only SELECT/WITH statement only."""
    statement = sql.strip().rstrip(";").strip()
    if not statement or ";" in statement:
        raise ValueError("Only one SQL statement is allowed.")
    if not re.match(r"^(SELECT|WITH)\b", statement, re.IGNORECASE):
        raise ValueError("Only SELECT queries are allowed.")
    if FORBIDDEN_SQL.search(statement):
        raise ValueError("Unsafe SQL statement rejected.")
    return statement


def execute_select_query(source: str | Path, sql: str) -> tuple[list[str], list[dict[str, Any]]]:
    """Load one CSV into the generic in-memory dataset table and execute a safe SELECT."""
    statement = validate_select_query(sql)
    dataframe = read_csv_with_fallback_encodings(source)
    with sqlite3.connect(":memory:") as connection:
        dataframe.to_sql(DATASET_TABLE_NAME, connection, index=False, if_exists="replace")
        cursor = connection.execute(statement)
        columns = [description[0] for description in cursor.description or []]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return columns, rows


def dataset_schema(source: str | Path) -> list[str]:
    """Return actual CSV column names for dynamic query construction."""
    return [str(column) for column in read_csv_with_fallback_encodings(source).columns]


def dataset_schema_with_types(source: str | Path) -> dict[str, str]:
    """Return the uploaded CSV's actual column names and inferred data types."""
    dataframe = read_csv_with_fallback_encodings(source)
    # Pandas 3 infers text CSV columns as ``str`` while earlier versions use
    # ``object``. Keep the schema sent to the SQL service version-independent.
    return {
        str(column): "object" if str(data_type) == "str" else str(data_type)
        for column, data_type in dataframe.dtypes.items()
    }


def _normalized_identifier(value: str) -> str:
    """Normalize a CSV header or question fragment for schema matching."""
    with_word_boundaries = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", " ", with_word_boundaries.casefold()).strip()


def _find_column(columns: list[str], name: str) -> str | None:
    target = _normalized_identifier(name)
    return next((column for column in columns if _normalized_identifier(column) == target), None)


def _mentioned_columns(columns: list[str], text: str) -> list[str]:
    """Return schema columns explicitly mentioned in text, longest names first."""
    normalized = _normalized_identifier(text)
    matches = [
        column for column in columns
        if re.search(rf"\b{re.escape(_normalized_identifier(column))}\b", normalized)
    ]
    return sorted(matches, key=lambda column: len(_normalized_identifier(column)), reverse=True)


def _grouping_column(columns: list[str], question: str) -> str | None:
    """Find the dimension named after a grouping cue such as 'by' or 'each'."""
    cue = re.search(r"\b(?:by|each|per)\b\s+(.+)", question, re.IGNORECASE)
    if cue:
        matches = _mentioned_columns(columns, cue.group(1))
        if matches:
            return matches[0]
    matches = _mentioned_columns(columns, question)
    return matches[0] if len(matches) == 1 else None


def _highest_aggregate_columns(columns: list[str], question: str) -> tuple[str, str] | None:
    """Find the group and measure in a highest-total question from the schema."""
    normalized = question.casefold()
    if not re.search(r"\b(?:highest|most|largest)\b", normalized):
        return None

    group = _grouping_column(columns, question)
    if not group:
        group_match = re.search(r"\b(?:which\s+)?(.+?)\s+(?:has|with)\s+(?:the\s+)?(?:highest|most|largest)\b", question, re.IGNORECASE)
        if group_match:
            matches = _mentioned_columns(columns, group_match.group(1))
            group = matches[0] if matches else None
    if not group:
        return None

    measure = next((column for column in _mentioned_columns(columns, question) if column != group), None)
    return (group, measure) if measure else None


def _highest_sum_query(group: str, measure: str) -> str:
    """Build a query for the group with the highest summed measure."""
    group_alias = _normalized_identifier(group).replace(" ", "_")
    total_alias = f"total_{_normalized_identifier(measure).replace(' ', '_')}"
    return (
        f"SELECT {quote_identifier(group)} AS {quote_identifier(group_alias)}, "
        f"SUM({quote_identifier(measure)}) AS {quote_identifier(total_alias)} "
        f"FROM {quote_identifier(DATASET_TABLE_NAME)} GROUP BY {quote_identifier(group)} "
        f"ORDER BY {quote_identifier(total_alias)} DESC LIMIT 1"
    )


def _aggregate_query(function: str, measure: str | None, group: str, alias: str, limit: int | None = None) -> str:
    aggregate = "COUNT(*)" if measure is None else f"{function}({quote_identifier(measure)})"
    sql = (
        f"SELECT {quote_identifier(group)} AS {quote_identifier(group)}, {aggregate} AS {alias} "
        f"FROM {quote_identifier(DATASET_TABLE_NAME)} GROUP BY {quote_identifier(group)}"
    )
    if limit:
        sql += f" ORDER BY {alias} DESC LIMIT {limit}"
    else:
        sql += f" ORDER BY {quote_identifier(group)}"
    return sql


def generate_query(question: str, columns: list[str]) -> str:
    """Build safe SQL for common dataset questions from the actual schema."""
    normalized = question.casefold()
    sales = _find_column(columns, "sales")
    profit = _find_column(columns, "profit")
    category = _find_column(columns, "category")
    region = _find_column(columns, "region")
    highest_aggregate = _highest_aggregate_columns(columns, question)
    if highest_aggregate:
        return _highest_sum_query(*highest_aggregate)
    if "region" in normalized and "profit" in normalized and region and profit:
        return (
            f"SELECT {quote_identifier(region)} AS region, "
            f"SUM({quote_identifier(profit)}) AS total_profit "
            f"FROM {quote_identifier(DATASET_TABLE_NAME)} GROUP BY {quote_identifier(region)} "
            "ORDER BY total_profit DESC LIMIT 1"
        )
    if "categor" in normalized and "sales" in normalized and category and sales:
        match = re.search(r"top\s+(\d+)", normalized)
        limit = int(match.group(1)) if match else 10
        return (
            f"SELECT {quote_identifier(category)} AS category, "
            f"SUM({quote_identifier(sales)}) AS total_sales "
            f"FROM {quote_identifier(DATASET_TABLE_NAME)} GROUP BY {quote_identifier(category)} "
            f"ORDER BY total_sales DESC LIMIT {limit}"
        )

    group = _grouping_column(columns, question)
    if not group:
        raise ValueError("The SQL Agent could not generate a safe query for this request and dataset schema.")

    if re.search(r"\b(?:how many|count|number of)\b", normalized):
        return _aggregate_query("COUNT", None, group, "count")

    average = re.search(r"\b(?:average|avg|mean)\b", normalized)
    if average:
        measure_candidates = _mentioned_columns(columns, question[:average.end()] + question[average.end():])
        measure = next((column for column in measure_candidates if column != group), None)
        if measure:
            return _aggregate_query("AVG", measure, group, f"average_{_normalized_identifier(measure).replace(' ', '_')}")

    if re.search(r"\b(?:most|highest|largest)\b", normalized):
        return _aggregate_query("COUNT", None, group, "count", limit=1)

    raise ValueError("The SQL Agent could not generate a safe query for this request and dataset schema.")
