"""Typed state passed between DataMind LangGraph workflow nodes."""

from typing import NotRequired, TypedDict

from app.models.data_profile import ChartSpecification, DatasetProfile, EdaResults
from app.models.sql_result import SqlResult


class WorkflowExecution(TypedDict):
    """A trace entry recording work completed by a graph node."""

    agent: str
    event: str
    intent: NotRequired[str]


class DataMindGraphState(TypedDict):
    """State for the first dataset analysis workflow."""

    file_id: str
    user_request: str
    dataset_profile: NotRequired[DatasetProfile | None]
    eda_results: NotRequired[EdaResults | None]
    sql_query: NotRequired[str | None]
    sql_result: NotRequired[SqlResult | None]
    insight: NotRequired[str | None]
    intent: NotRequired[str]
    visualization_results: NotRequired[list[ChartSpecification]]
    run_sql: NotRequired[bool]
    current_agent: str
    execution: list[WorkflowExecution]
