"""Tests for the graph-backed SQL query endpoint."""

from fastapi.testclient import TestClient

from app import main
from app.agents.insight_agent import InsightAgent
from app.agents.manager_agent import ManagerAgent
from app.agents.sql_agent import SqlAgent
from app.graph import workflow
from app.services.llm_service import GroqSqlService
from app.tools import data_tools
from app.tools.sql_tools import generate_query


class FakeGroqSqlService:
    """Offline SQL generator for graph/API tests."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, str]]] = []

    def generate_sql(self, question: str, table_name: str, schema: dict[str, str]) -> str:
        self.calls.append((question, table_name, schema))
        return generate_query(question, list(schema))


class FakeGroqInsightService:
    """Offline result interpreter for graph/API tests."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, list[str], list[dict[str, object]]]] = []

    def generate_insight(self, question, sql, columns, rows) -> str:
        self.calls.append((question, sql, columns, rows))
        return f"Answer based on {rows[0][columns[0]]}."


class FakeGroqManagerService:
    """Offline intent classifier for query workflow tests."""

    def __init__(self, intent: str = "query") -> None:
        self.intent = intent

    def generate_intent(self, _user_request: str) -> str:
        return f'{{"intent": "{self.intent}"}}'


def _install_fake_query_agents(monkeypatch, intent: str = "query") -> tuple[FakeGroqSqlService, FakeGroqInsightService]:
    """Replace the graph's production agent without changing app behavior."""
    service = FakeGroqSqlService()
    insight_service = FakeGroqInsightService()

    def fail_if_real_groq_is_called(*_args, **_kwargs):
        raise AssertionError("API tests must not call the real Groq service.")

    monkeypatch.setattr(GroqSqlService, "generate_sql", fail_if_real_groq_is_called)
    monkeypatch.setattr(GroqSqlService, "generate_insight", fail_if_real_groq_is_called)
    monkeypatch.setattr(GroqSqlService, "generate_intent", fail_if_real_groq_is_called)
    monkeypatch.setattr(workflow, "manager_agent", ManagerAgent(llm_service=FakeGroqManagerService(intent)))
    monkeypatch.setattr(workflow, "sql_agent", SqlAgent(llm_service=service))
    monkeypatch.setattr(workflow, "insight_agent", InsightAgent(llm_service=insight_service))
    return service, insight_service


def test_agent_query_returns_sqlite_backed_result(tmp_path, monkeypatch) -> None:
    file_id = "8" * 32
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / f"{file_id}.csv").write_bytes(b"Region,Sales,Profit\nEast,100,10\nWest,300,60\n")
    monkeypatch.setattr(data_tools, "UPLOADS_DIRECTORY", uploads)
    service, insight_service = _install_fake_query_agents(monkeypatch)
    client = TestClient(main.app)

    response = client.post(f"/agent/query/{file_id}", params={"user_request": "Which region has the highest profit?"})

    assert response.status_code == 200
    body = response.json()
    assert body["sql_result"]["rows"] == [{"region": "West", "total_profit": 60}]
    assert body["sql_result"]["row_count"] == 1
    assert body["insight"] == "Answer based on West."
    assert body["visualization_results"] == []
    assert body["execution"][-3:] == [
        {"agent": "sql_agent", "event": "query_completed"},
        {"agent": "sql_agent", "event": "routed_to_insight_agent"},
        {"agent": "insight_agent", "event": "insight_generated"},
    ]
    assert body["execution"][0] == {"agent": "manager", "event": "classified_request", "intent": "query"}
    assert service.calls[0][0] == "Which region has the highest profit?"
    assert insight_service.calls[0][2:] == (["region", "total_profit"], [{"region": "West", "total_profit": 60}])


def test_agent_query_returns_not_found_for_invalid_file_id() -> None:
    response = TestClient(main.app).post(f"/agent/query/{'0' * 32}", params={"user_request": "Which region has the highest profit?"})

    assert response.status_code == 404


def test_agent_query_supports_hr_schema(tmp_path, monkeypatch) -> None:
    file_id = "6" * 32
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / f"{file_id}.csv").write_bytes(
        b"Age,Attrition,Department,MonthlyIncome\n"
        b"30,Yes,Sales,5000\n40,No,HR,7000\n20,Yes,Sales,4000\n50,No,HR,9000\n"
    )
    monkeypatch.setattr(data_tools, "UPLOADS_DIRECTORY", uploads)
    service, insight_service = _install_fake_query_agents(monkeypatch)

    response = TestClient(main.app).post(
        f"/agent/query/{file_id}",
        params={"user_request": "How many employees are in each attrition category?"},
    )

    assert response.status_code == 200
    assert response.json()["sql_result"]["rows"] == [
        {"Attrition": "No", "count": 2},
        {"Attrition": "Yes", "count": 2},
    ]
    assert service.calls[0][0] == "How many employees are in each attrition category?"
    assert insight_service.calls[0][0] == "How many employees are in each attrition category?"


def test_agent_query_routes_analysis_intent_without_sql_or_insight(tmp_path, monkeypatch) -> None:
    file_id = "7" * 32
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / f"{file_id}.csv").write_bytes(b"Region,Sales,Profit\nEast,100,10\nWest,300,60\n")
    monkeypatch.setattr(data_tools, "UPLOADS_DIRECTORY", uploads)
    service, insight_service = _install_fake_query_agents(monkeypatch, intent="analysis")

    response = TestClient(main.app).post(
        f"/agent/query/{file_id}",
        params={"user_request": "Analyze this dataset and identify the key patterns."},
    )

    assert response.status_code == 200
    body = response.json()
    assert "sql_result" not in body
    assert body["visualization_results"]
    assert body["execution"] == [
        {"agent": "manager", "event": "classified_request", "intent": "analysis"},
        {"agent": "data_agent", "event": "profile_completed"},
        {"agent": "data_agent", "event": "routed_to_eda_agent"},
        {"agent": "eda_agent", "event": "analysis_completed"},
        {"agent": "visualization_agent", "event": "visualizations_created"},
    ]
    assert service.calls == []
    assert insight_service.calls == []
