"""Reusable Pandas-based tools for loading and profiling datasets."""

from __future__ import annotations

import math
import re
import warnings
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError, ParserError

from app.models.data_profile import DataQualityIssues, DatasetProfile


FILE_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$", re.IGNORECASE)
NON_NUMERIC_DTYPES = ["object", "string", "category", "bool"]
CSV_ENCODINGS = ("utf-8", "utf-8-sig", "cp1252", "latin1")
UPLOADS_DIRECTORY = Path(__file__).resolve().parents[2] / "data" / "uploads"


def resolve_dataset_source(source: str | Path) -> Path:
    """Resolve a trusted CSV path or a DataMind upload identifier."""
    source_path = Path(source)
    if source_path.is_file():
        return source_path

    source_value = str(source)
    if FILE_ID_PATTERN.fullmatch(source_value):
        upload_path = UPLOADS_DIRECTORY / f"{source_value}.csv"
        if upload_path.is_file():
            return upload_path

    raise FileNotFoundError("Dataset file was not found.")


def read_csv_with_fallback_encodings(path: str | Path) -> pd.DataFrame:
    """Read a stored CSV with the same encoding fallback sequence as uploads."""
    dataset_path = resolve_dataset_source(path)
    contents = dataset_path.read_bytes()
    if not contents:
        raise ValueError("The dataset CSV is empty.")

    for encoding in CSV_ENCODINGS:
        try:
            return pd.read_csv(BytesIO(contents), encoding=encoding)
        except UnicodeDecodeError:
            continue
        except (EmptyDataError, ParserError) as error:
            raise ValueError("The dataset CSV could not be parsed.") from error

    raise ValueError("Unable to decode the dataset using supported CSV encodings.")


def _is_string_like(series: pd.Series) -> bool:
    return pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)


def _mostly_parseable(series: pd.Series, parser: Any) -> bool:
    non_null = series.dropna()
    if non_null.empty:
        return False
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        parsed = parser(non_null, errors="coerce")
    return parsed.notna().mean() >= 0.8


def _parse_dates(values: pd.Series, *, errors: str) -> pd.Series:
    """Parse mixed-format date strings across supported Pandas versions."""
    try:
        return pd.to_datetime(values, errors=errors, format="mixed")
    except (TypeError, ValueError):
        return pd.to_datetime(values, errors=errors)


def _possible_date_columns(dataframe: pd.DataFrame) -> list[str]:
    return [
        str(column)
        for column in dataframe.columns
        if _is_string_like(dataframe[column])
        and _mostly_parseable(dataframe[column], _parse_dates)
    ]


def _numeric_string_columns(dataframe: pd.DataFrame) -> list[str]:
    return [
        str(column)
        for column in dataframe.columns
        if _is_string_like(dataframe[column])
        and _mostly_parseable(dataframe[column], pd.to_numeric)
    ]


def _json_safe(value: Any) -> Any:
    """Convert Pandas/NumPy scalars and missing values into plain Python values."""
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _numerical_statistics(dataframe: pd.DataFrame, columns: list[str]) -> dict[str, dict[str, Any]]:
    if not columns:
        return {}
    statistics = dataframe[columns].describe().to_dict()
    return {
        str(column): {str(name): _json_safe(value) for name, value in values.items()}
        for column, values in statistics.items()
    }


def profile_dataframe(dataframe: pd.DataFrame) -> DatasetProfile:
    """Produce a deterministic profile using Pandas only."""
    numerical_columns = [str(column) for column in dataframe.select_dtypes(include="number").columns]
    categorical_columns = [
        str(column)
        for column in dataframe.select_dtypes(include=NON_NUMERIC_DTYPES).columns
    ]
    missing_counts = {str(column): int(count) for column, count in dataframe.isna().sum().items()}
    row_count = len(dataframe.index)
    missing_percentages = {
        column: round((count / row_count) * 100, 2) if row_count else 0.0
        for column, count in missing_counts.items()
    }
    unique_counts = {str(column): int(count) for column, count in dataframe.nunique().items()}
    duplicate_row_count = int(dataframe.duplicated().sum())
    single_value_columns = [column for column, count in unique_counts.items() if count == 1]
    possible_dates = _possible_date_columns(dataframe)
    numeric_strings = _numeric_string_columns(dataframe)

    return DatasetProfile(
        row_count=row_count,
        column_count=len(dataframe.columns),
        column_names=[str(column) for column in dataframe.columns],
        data_types={str(column): str(data_type) for column, data_type in dataframe.dtypes.items()},
        numerical_columns=numerical_columns,
        categorical_columns=categorical_columns,
        missing_value_counts=missing_counts,
        missing_value_percentages=missing_percentages,
        duplicate_row_count=duplicate_row_count,
        unique_value_counts=unique_counts,
        numerical_descriptive_statistics=_numerical_statistics(dataframe, numerical_columns),
        data_quality_issues=DataQualityIssues(
            missing_value_columns=[column for column, count in missing_counts.items() if count > 0],
            duplicate_row_count=duplicate_row_count,
            single_value_columns=single_value_columns,
            possible_date_columns=possible_dates,
            numeric_string_columns=numeric_strings,
        ),
    )
