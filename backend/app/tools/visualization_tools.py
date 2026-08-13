"""Build frontend-ready chart specifications from results already in graph state."""

from __future__ import annotations

from typing import Any

from app.models.data_profile import ChartSpecification, EdaResults
from app.models.sql_result import SqlResult


def choose_chart_type(*, analysis_kind: str, data: list[dict[str, Any]]) -> str:
    """Choose a chart type from the shape and intent of upstream analysis."""
    if analysis_kind == "time_series":
        return "line"
    if analysis_kind == "relationship":
        return "scatter"
    if analysis_kind == "proportion":
        return "pie"
    return "bar"


def _spec(chart_type: str, title: str, x_axis: str, y_axis: str, data: list[dict[str, Any]]) -> ChartSpecification:
    return ChartSpecification(chart_type=chart_type, title=title, x_axis=x_axis, y_axis=y_axis, data=data)


def _categorical_chart(eda: EdaResults, key: str, title: str, y_axis: str) -> ChartSpecification | None:
    data = eda.categorical_analysis.get(key, [])
    if not data:
        return None
    x_axis = next((name for name in data[0] if name != y_axis), "category")
    return _spec(choose_chart_type(analysis_kind="comparison", data=data), title, x_axis, y_axis, data)


def _title_from_grouping_key(key: str) -> str:
    """Convert an EDA grouping key such as ``sales_by_city`` into a title."""
    metric, dimension = key.split("_by_", maxsplit=1)
    if key == "count_by_attrition":
        return "Attrition Distribution"
    metric_label = "Record Count" if metric == "count" else metric.replace("_", " ").title()
    return f"{metric_label} by {dimension.replace('_', ' ').title()}"


def _generic_chart_keys(analysis: dict[str, list[dict[str, Any]]]) -> list[str]:
    """Select a small, useful set of generic category summaries."""
    keys = [key for key, data in analysis.items() if data and (key.startswith("count_by_") or key.startswith("average_") or key.startswith("sales_by_"))]
    preferred_dimensions = ("attrition", "department", "businesstravel", "educationfield")

    def rank(key: str) -> tuple[int, str]:
        dimension = key.split("_by_", maxsplit=1)[-1]
        metric = key.split("_by_", maxsplit=1)[0]
        # Show distributions across important dimensions before adding one
        # contextual average where it is particularly useful.
        priority = {
            ("attrition", "count"): 0,
            ("attrition", "average_age"): 1,
            ("department", "count"): 2,
            ("department", "average_monthlyincome"): 3,
            ("businesstravel", "count"): 4,
            ("educationfield", "count"): 5,
        }.get((next((name for name in preferred_dimensions if name in dimension), ""), metric), 10)
        return (priority, key)

    return sorted(keys, key=rank)[:6]


def build_visualizations(eda_results: EdaResults, sql_result: SqlResult | None = None) -> list[ChartSpecification]:
    """Translate EDA and optional SQL output into charts; never read the dataset."""
    charts: list[ChartSpecification] = []
    for key, title, metric in (
        ("sales_by_region", "Sales by Region", "sales"),
        ("profit_by_region", "Profit by Region", "profit"),
        ("sales_by_category", "Sales by Category", "sales"),
        ("profit_by_category", "Profit by Category", "profit"),
        ("sales_by_segment", "Sales by Segment", "sales"),
        ("profit_by_segment", "Profit by Segment", "profit"),
        ("top_products_by_sales", "Top Products by Sales", "sales"),
        ("top_products_by_profit", "Top Products by Profit", "profit"),
    ):
        chart = _categorical_chart(eda_results, key, title, metric)
        if chart:
            charts.append(chart)

    # EDA also supplies dynamic ``metric_by_dimension`` summaries for datasets
    # outside the sales schema.  Discover those summaries instead of assuming
    # Region, Category, or Profit exist.  Explicit sales charts above retain
    # their familiar titles and are not duplicated here.
    handled_keys = {chart.title for chart in charts}
    for key in _generic_chart_keys(eda_results.categorical_analysis):
        data = eda_results.categorical_analysis[key]
        metric = "count" if key.startswith("count_by_") else key.split("_by_", maxsplit=1)[0]
        if metric not in data[0]:
            continue
        title = _title_from_grouping_key(key)
        if title in handled_keys:
            continue
        x_axis = next((name for name in data[0] if name != metric), "category")
        kind = "proportion" if key == "count_by_attrition" else "comparison"
        charts.append(_spec(choose_chart_type(analysis_kind=kind, data=data), title, x_axis, metric, data))

    for key, title, metric in (
        ("sales_by_month", "Sales over Time", "sales"),
        ("profit_by_month", "Profit over Time", "profit"),
    ):
        data = eda_results.time_analysis.get(key, [])
        if data:
            charts.append(_spec(choose_chart_type(analysis_kind="time_series", data=data), title, "period", metric, data))

    sales_profit = eda_results.relationship_data.get("sales_vs_profit", [])
    if sales_profit:
        charts.append(_spec(choose_chart_type(analysis_kind="relationship", data=sales_profit), "Sales vs Profit", "sales", "profit", sales_profit))

    # SQL rows are already materialized upstream. Add a result chart only when
    # it has a categorical label and one numeric measure.
    if sql_result and sql_result.rows:
        columns = list(sql_result.rows[0])
        if len(columns) >= 2:
            charts.append(_spec(choose_chart_type(analysis_kind="comparison", data=sql_result.rows), "SQL Query Result", columns[0], columns[1], sql_result.rows))
    return charts
