"""Tests for the graph-backed dataset analysis API endpoint."""

from fastapi.testclient import TestClient

from app import main
from app.tools import data_tools


def _create_uploaded_csv(tmp_path, file_id: str, contents: bytes) -> None:
    upload_directory = tmp_path / "uploads"
    upload_directory.mkdir()
    (upload_directory / f"{file_id}.csv").write_bytes(contents)


def test_agent_analysis_returns_profile_and_execution_trace(tmp_path, monkeypatch) -> None:
    file_id = "d" * 32
    _create_uploaded_csv(tmp_path, file_id, b"city,sales\nDelhi,100\nMumbai,200\n")
    monkeypatch.setattr(data_tools, "UPLOADS_DIRECTORY", tmp_path / "uploads")
    client = TestClient(main.app)

    response = client.post(f"/agent/analyze/{file_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["dataset_profile"]["row_count"] == 2
    assert body["dataset_profile"]["column_names"] == ["city", "sales"]
    assert body["eda_results"]
    assert body["eda_results"]["overall_metrics"]["total_sales"] == 300.0
    assert "total_profit" not in body["eda_results"]["overall_metrics"]
    assert body["visualization_results"]
    assert body["execution"] == [
        {"agent": "manager", "event": "routed_to_data_agent"},
        {"agent": "data_agent", "event": "profile_completed"},
        {"agent": "data_agent", "event": "routed_to_eda_agent"},
        {"agent": "eda_agent", "event": "analysis_completed"},
        {"agent": "visualization_agent", "event": "visualizations_created"},
    ]


def test_agent_analysis_returns_not_found_for_non_existent_file_id() -> None:
    client = TestClient(main.app)

    response = client.post(f"/agent/analyze/{'e' * 32}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Dataset file was not found."}


def test_agent_analysis_accepts_optional_user_request(tmp_path, monkeypatch) -> None:
    file_id = "f" * 32
    _create_uploaded_csv(tmp_path, file_id, b"city,sales\nDelhi,100\n")
    monkeypatch.setattr(data_tools, "UPLOADS_DIRECTORY", tmp_path / "uploads")
    client = TestClient(main.app)

    response = client.post(
        f"/agent/analyze/{file_id}",
        params={"user_request": "Profile sales by city."},
    )

    assert response.status_code == 200
    assert response.json()["execution"][0]["agent"] == "manager"


def test_agent_analysis_returns_error_for_unanalyzable_dataset(tmp_path, monkeypatch) -> None:
    file_id = "1" * 32
    _create_uploaded_csv(tmp_path, file_id, b"city,sales\nDelhi,100\nMumbai,200,extra\n")
    monkeypatch.setattr(data_tools, "UPLOADS_DIRECTORY", tmp_path / "uploads")
    client = TestClient(main.app)

    response = client.post(f"/agent/analyze/{file_id}")

    assert response.status_code == 422
    assert response.json() == {"detail": "Dataset could not be analyzed."}
