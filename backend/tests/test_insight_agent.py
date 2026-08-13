"""Tests for SQL-result-grounded Insight Agent behavior."""

from app.agents.insight_agent import EMPTY_RESULT_INSIGHT, InsightAgent


class FakeInsightService:
    """Captures supplied SQL results without contacting Groq."""

    def __init__(self) -> None:
        self.call = None

    def generate_insight(self, question, sql, columns, rows) -> str:
        self.call = (question, sql, columns, rows)
        return "West has the highest total profit at approximately $67,860.56."


def test_insight_agent_uses_fake_service_with_completed_sql_result() -> None:
    service = FakeInsightService()
    result = InsightAgent(llm_service=service).generate(
        "Which region has the highest profit?",
        'SELECT "Region", SUM("Profit") AS "total_profit" FROM "dataset" GROUP BY "Region"',
        ["Region", "total_profit"],
        [{"Region": "West", "total_profit": 67860.563}],
    )

    assert result == "West has the highest total profit at approximately $67,860.56."
    assert service.call == (
        "Which region has the highest profit?",
        'SELECT "Region", SUM("Profit") AS "total_profit" FROM "dataset" GROUP BY "Region"',
        ["Region", "total_profit"],
        [{"Region": "West", "total_profit": 67860.563}],
    )


def test_insight_agent_returns_controlled_message_for_empty_result() -> None:
    service = FakeInsightService()

    result = InsightAgent(llm_service=service).generate(
        "Which region has the highest profit?",
        'SELECT "Region" FROM "dataset" WHERE 1 = 0',
        ["Region"],
        [],
    )

    assert result == EMPTY_RESULT_INSIGHT
    assert service.call is None
