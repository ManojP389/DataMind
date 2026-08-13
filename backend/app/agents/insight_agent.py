"""Insight Agent that explains completed SQL results using Groq."""

from app.services.llm_service import GroqSqlService, InsightGenerationService


EMPTY_RESULT_INSIGHT = "No matching data was found for this question."


class InsightAgent:
    """Generate a concise, result-grounded answer without executing SQL."""

    def __init__(self, llm_service: InsightGenerationService | None = None) -> None:
        self.llm_service = llm_service or GroqSqlService()

    def generate(self, question: str, sql: str, columns: list[str], rows: list[dict[str, object]]) -> str:
        """Explain SQL rows, or return a deterministic message for an empty result."""
        if not rows:
            return EMPTY_RESULT_INSIGHT
        return self.llm_service.generate_insight(question, sql, columns, rows)
