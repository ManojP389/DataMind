"""Tests for LLM-backed, validated Ask DataMind intent classification."""

from app.agents.manager_agent import ManagerAgent
from app.graph import workflow
from app.models.sql_result import SqlResult


class FakeIntentService:
    def __init__(self, response: str | Exception) -> None:
        self.response = response

    def generate_intent(self, _user_request: str) -> str:
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _state(request: str) -> dict[str, object]:
    return {"file_id": "a" * 32, "user_request": request, "current_agent": "", "execution": []}


def test_manager_classifies_query_from_valid_llm_json() -> None:
    result = ManagerAgent(FakeIntentService('{"intent": "query"}')).classify_query_request(_state("What is the average salary?"))

    assert result["intent"] == "query"


def test_manager_classifies_analysis_from_valid_llm_json() -> None:
    result = ManagerAgent(FakeIntentService('{"intent": "analysis"}')).classify_query_request(_state("Analyze the dataset"))

    assert result["intent"] == "analysis"


def test_manager_uses_deterministic_fallback_for_invalid_llm_output() -> None:
    result = ManagerAgent(FakeIntentService('{"intent": "other"}')).classify_query_request(_state("Give me an overview of the dataset"))

    assert result["intent"] == "analysis"


def test_manager_uses_deterministic_fallback_when_llm_fails() -> None:
    result = ManagerAgent(FakeIntentService(RuntimeError("offline"))).classify_query_request(_state("Which region has the highest profit?"))

    assert result["intent"] == "query"


def test_query_workflow_uses_sql_and_insight_without_visualization(monkeypatch) -> None:
    calls: list[str] = []
    sql_result = SqlResult(
        question="Which region has the highest profit?",
        sql='SELECT "Region" FROM "dataset"',
        columns=["Region"],
        rows=[{"Region": "West"}],
        row_count=1,
    )

    monkeypatch.setattr(workflow, "manager_agent", ManagerAgent(FakeIntentService('{"intent": "query"}')))
    monkeypatch.setattr(workflow.sql_agent, "query", lambda *_args: calls.append("sql") or sql_result)
    monkeypatch.setattr(workflow.insight_agent, "generate", lambda *_args: calls.append("insight") or "done")
    monkeypatch.setattr(workflow.visualization_agent, "create", lambda *_args: calls.append("visualization") or [])

    final_state = workflow.build_query_workflow().invoke(_state("Which region has the highest profit?"))

    assert calls == ["sql", "insight"]
    assert final_state["insight"] == "done"
    assert all(item["agent"] != "visualization_agent" for item in final_state["execution"])


def test_query_workflow_routes_analysis_intent_to_data_eda_and_visualization(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(workflow, "manager_agent", ManagerAgent(FakeIntentService('{"intent": "analysis"}')))
    monkeypatch.setattr(workflow.data_profiling_agent, "profile", lambda *_args: calls.append("data") or object())
    monkeypatch.setattr(workflow.eda_agent, "analyze", lambda *_args: calls.append("eda") or object())
    monkeypatch.setattr(workflow.visualization_agent, "create", lambda *_args: calls.append("visualization") or [])
    monkeypatch.setattr(workflow.sql_agent, "query", lambda *_args: calls.append("sql"))
    monkeypatch.setattr(workflow.insight_agent, "generate", lambda *_args: calls.append("insight"))

    workflow.build_query_workflow().invoke(_state("Analyze this dataset and identify the key patterns."))

    assert calls == ["data", "eda", "visualization"]


def test_manager_execution_trace_is_recorded() -> None:
    result = ManagerAgent(FakeIntentService('{"intent": "query"}')).classify_query_request(_state("How many employees are in each department?"))

    assert result["execution"] == [{"agent": "manager", "event": "classified_request", "intent": "query"}]
