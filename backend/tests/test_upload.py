"""Tests for CSV dataset upload."""

from fastapi.testclient import TestClient

from app.main import app
from app.services import upload_service


def test_upload_utf8_csv_returns_dataset_metadata(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(upload_service, "UPLOADS_DIRECTORY", tmp_path / "uploads")
    client = TestClient(app)

    response = client.post(
        "/upload",
        files={
            "file": (
                "sales_data.csv",
                b"region,revenue\nNorth,125.5\nSouth,90\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "sales_data.csv"
    assert len(body["file_id"]) == 32
    assert body["rows"] == 2
    assert body["columns"] == 2
    assert body["column_names"] == ["region", "revenue"]
    assert body["data_types"]["region"] in {"object", "str"}
    assert body["data_types"]["revenue"] == "float64"
    assert not any("path" in key for key in body)
    assert (tmp_path / "uploads" / f"{body['file_id']}.csv").is_file()


def test_upload_latin1_csv_returns_dataset_metadata(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(upload_service, "UPLOADS_DIRECTORY", tmp_path / "uploads")
    client = TestClient(app)

    response = client.post(
        "/upload",
        files={"file": ("sales_data.csv", b"city,revenue\nCaf\xe9,100\n", "text/csv")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["rows"] == 1
    assert body["columns"] == 2
    assert body["column_names"] == ["city", "revenue"]


def test_upload_rejects_non_csv_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(upload_service, "UPLOADS_DIRECTORY", tmp_path / "uploads")
    client = TestClient(app)

    response = client.post(
        "/upload",
        files={"file": ("notes.txt", b"not a dataset", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json() == {"detail": "Only CSV files are supported."}
    assert not (tmp_path / "uploads").exists()


def test_upload_reports_csv_parser_error_in_development(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(upload_service, "UPLOADS_DIRECTORY", tmp_path / "uploads")
    client = TestClient(app)

    response = client.post(
        "/upload",
        files={
            "file": (
                "broken.csv",
                b"region,revenue\nNorth,100\nSouth,90,unexpected\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"].startswith("CSV parsing failed: ParserError:")
    assert not list((tmp_path / "uploads").glob("*.csv"))


def test_upload_rejects_empty_csv(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(upload_service, "UPLOADS_DIRECTORY", tmp_path / "uploads")
    client = TestClient(app)

    response = client.post(
        "/upload",
        files={"file": ("empty.csv", b"", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "The uploaded CSV is empty."}
    assert not list((tmp_path / "uploads").glob("*.csv"))
