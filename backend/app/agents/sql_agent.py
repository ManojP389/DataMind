"""SQL Agent that turns supported natural-language questions into SQLite queries."""

from pathlib import Path

from app.models.sql_result import SqlResult
from app.services.llm_service import GroqSqlService, SqlGenerationService, extract_sql
from app.tools.sql_tools import (
    DATASET_TABLE_NAME,
    dataset_schema_with_types,
    execute_select_query,
    generate_query,
    validate_select_query,
)


class SqlAgent:
    """Inspect a CSV schema, generate supported SQL, and execute it in SQLite."""

    def __init__(self, llm_service: SqlGenerationService | None = None) -> None:
        self.llm_service = llm_service or GroqSqlService()

    def query(self, file_id: str | Path, user_request: str) -> SqlResult:
        schema = dataset_schema_with_types(file_id)
        try:
            sql = self.llm_service.generate_sql(user_request, DATASET_TABLE_NAME, schema)
        except RuntimeError as error:
            # Preserve the existing offline SQL workflow when no Groq key is
            # configured. Configured Groq failures are surfaced to the API.
            if str(error) != "GROQ_API_KEY is not configured.":
                raise
            sql = generate_query(user_request, list(schema))
        # The production Groq service normalizes fenced output, but keep the
        # agent boundary tolerant of any compatible SQL provider as well.
        sql = validate_select_query(extract_sql(sql))
        result_columns, rows = execute_select_query(file_id, sql)
        return SqlResult(
            question=user_request,
            sql=sql,
            columns=result_columns,
            rows=rows,
            row_count=len(rows),
        )
