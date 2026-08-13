"""CSV upload storage and profiling operations."""

from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pandas as pd
from fastapi import UploadFile
from pandas.errors import EmptyDataError, ParserError

from app.models.dataset import DatasetUploadResponse


DATA_DIRECTORY = Path(__file__).resolve().parents[2] / "data"
UPLOADS_DIRECTORY = DATA_DIRECTORY / "uploads"
ALLOWED_CONTENT_TYPES = {"text/csv", "application/csv", "application/vnd.ms-excel"}
IS_DEVELOPMENT = os.getenv("DATAMIND_ENV", "development").lower() == "development"
CSV_ENCODINGS = ("utf-8", "utf-8-sig", "cp1252", "latin1")


class InvalidDatasetError(Exception):
    """An upload that cannot be accepted as a CSV dataset."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _safe_filename(filename: str | None) -> str:
    """Return only the final filename component supplied by a client."""
    return (filename or "").replace("\\", "/").rsplit("/", maxsplit=1)[-1]


def _validate_upload(file: UploadFile) -> str:
    filename = _safe_filename(file.filename)
    if not filename or not filename.lower().endswith(".csv"):
        raise InvalidDatasetError("Only CSV files are supported.", status_code=415)

    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise InvalidDatasetError("Uploaded content must have a CSV media type.", status_code=415)

    return filename


def _parsing_error_message(error: Exception) -> str:
    """Avoid leaking parser internals outside the development environment."""
    if IS_DEVELOPMENT:
        return f"CSV parsing failed: {type(error).__name__}: {error}"
    return "The uploaded file is not a valid CSV dataset."


async def load_csv_with_fallback_encodings(file: UploadFile) -> tuple[pd.DataFrame, bytes]:
    """Load a CSV by trying the supported encodings in a fixed, safe order."""
    for encoding in CSV_ENCODINGS:
        try:
            # Each attempt begins from the upload's start, even if a preceding
            # reader consumed the multipart stream.
            await file.seek(0)
            contents = await file.read()
            if not contents:
                raise InvalidDatasetError("The uploaded CSV is empty.")

            dataframe = pd.read_csv(BytesIO(contents), encoding=encoding)
            return dataframe, contents
        except UnicodeDecodeError:
            continue
        except (EmptyDataError, ParserError, ValueError) as error:
            raise InvalidDatasetError(_parsing_error_message(error)) from error

    raise InvalidDatasetError(
        "Unable to decode the uploaded CSV using UTF-8, UTF-8-SIG, Windows-1252, or Latin-1."
    )


async def process_csv_upload(file: UploadFile) -> DatasetUploadResponse:
    """Validate, store, and load an uploaded CSV without exposing its location."""
    filename = _validate_upload(file)
    file_id = uuid4().hex
    UPLOADS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    stored_file = UPLOADS_DIRECTORY / f"{file_id}.csv"

    try:
        dataframe, contents = await load_csv_with_fallback_encodings(file)
        stored_file.write_bytes(contents)
    except InvalidDatasetError:
        if stored_file.exists():
            stored_file.unlink()
        raise
    except (EmptyDataError, ParserError, UnicodeDecodeError, ValueError) as error:
        if stored_file.exists():
            stored_file.unlink()
        raise InvalidDatasetError(_parsing_error_message(error)) from error
    finally:
        await file.close()

    return DatasetUploadResponse(
        file_id=file_id,
        filename=filename,
        rows=len(dataframe.index),
        columns=len(dataframe.columns),
        column_names=[str(column) for column in dataframe.columns],
        data_types={str(column): str(data_type) for column, data_type in dataframe.dtypes.items()},
    )
