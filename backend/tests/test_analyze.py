"""Tests for the Data Profiling Agent API endpoint."""

from fastapi.testclient import TestClient

from app import main
from app.tools import data_tools


def test_analyze_uploaded_dataset(tmp_path, monkeypatch) -> None:
    upload_directory = tmp_path / "uploads"
    upload_directory.mkdir()
    file_id = "a" * 32
    (upload_directory / f"{file_id}.csv").write_bytes(b"city,sales\nDelhi,100\nMumbai,200\n")
    monkeypatch.setattr(data_tools, "UPLOADS_DIRECTORY", upload_directory)
    client = TestClient(main.app)

    response = client.post(f"/analyze/{file_id}")

    assert response.status_code == 200
    assert response.json()["row_count"] == 2
    assert response.json()["column_count"] == 2
    assert response.json()["column_names"] == ["city", "sales"]
    assert response.json()["numerical_columns"] == ["sales"]


def test_analyze_returns_not_found_for_invalid_file_id() -> None:
    client = TestClient(main.app)

    response = client.post("/analyze/not-a-file-id")

    assert response.status_code == 404
    assert response.json() == {"detail": "Dataset file was not found."}


def test_analyze_returns_error_when_dataset_cannot_be_analyzed(tmp_path, monkeypatch) -> None:
    upload_directory = tmp_path / "uploads"
    upload_directory.mkdir()
    file_id = "b" * 32
    (upload_directory / f"{file_id}.csv").write_bytes(b"city,sales\nDelhi,100\nMumbai,200,extra\n")
    monkeypatch.setattr(data_tools, "UPLOADS_DIRECTORY", upload_directory)
    client = TestClient(main.app)

    response = client.post(f"/analyze/{file_id}")

    assert response.status_code == 422
    assert response.json() == {"detail": "Dataset could not be analyzed."}
