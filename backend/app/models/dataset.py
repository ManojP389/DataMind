"""Schemas for uploaded datasets."""

from pydantic import BaseModel


class DatasetUploadResponse(BaseModel):
    """Safe metadata about a stored CSV dataset."""

    file_id: str
    filename: str
    rows: int
    columns: int
    column_names: list[str]
    data_types: dict[str, str]
