"""Structured results produced by the Data Profiling Agent."""

from typing import Any

from pydantic import BaseModel, Field

from app.models.sql_result import SqlResult


class DataQualityIssues(BaseModel):
    """Basic quality signals derived from a dataset."""

    missing_value_columns: list[str]
    duplicate_row_count: int
    single_value_columns: list[str]
    possible_date_columns: list[str]
    numeric_string_columns: list[str]


class DatasetProfile(BaseModel):
    """A data-only profile suitable for a future workflow node."""

    row_count: int
    column_count: int
    column_names: list[str]
    data_types: dict[str, str]
    numerical_columns: list[str]
    categorical_columns: list[str]
    missing_value_counts: dict[str, int]
    missing_value_percentages: dict[str, float]
    duplicate_row_count: int
    unique_value_counts: dict[str, int]
    numerical_descriptive_statistics: dict[str, dict[str, Any]]
    data_quality_issues: DataQualityIssues


class EdaResults(BaseModel):
    """Structured, Pandas-derived exploratory analysis findings."""

    overall_metrics: dict[str, float | None]
    categorical_analysis: dict[str, list[dict[str, Any]]]
    time_analysis: dict[str, list[dict[str, Any]]]
    correlations: dict[str, dict[str, float | None]]
    relationships: dict[str, float | None]
    relationship_data: dict[str, list[dict[str, float | None]]]
    business_insights: dict[str, Any]


class ChartSpecification(BaseModel):
    """Frontend-neutral chart definition produced from analysis already in graph state."""

    chart_type: str
    title: str
    x_axis: str
    y_axis: str
    data: list[dict[str, Any]]


class AgentAnalysisResponse(BaseModel):
    """Final result returned by the graph-backed dataset analysis endpoint."""

    dataset_profile: DatasetProfile
    eda_results: EdaResults
    visualization_results: list[ChartSpecification]
    execution: list[dict[str, str]]


class AgentQueryResponse(BaseModel):
    """Final graph-backed SQL query response."""

    sql_result: SqlResult
    insight: str
    visualization_results: list[ChartSpecification] = Field(default_factory=list)
    execution: list[dict[str, str]]
