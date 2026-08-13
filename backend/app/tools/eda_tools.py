"""Reusable Pandas-only exploratory data analysis operations."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.models.data_profile import DatasetProfile, EdaResults
from app.tools.data_tools import read_csv_with_fallback_encodings


def _column(dataframe: pd.DataFrame, name: str) -> str | None:
    return next((str(column) for column in dataframe.columns if str(column).casefold() == name.casefold()), None)


def _field_name(column: str) -> str:
    return "_".join(column.casefold().split())


def _records(grouped: pd.Series, value_name: str, *, ascending: bool = False, limit: int | None = None) -> list[dict[str, Any]]:
    ordered = grouped.sort_values(ascending=ascending)
    if limit is not None:
        ordered = ordered.head(limit)
    return [{str(grouped.index.name): str(index), value_name: float(value)} for index, value in ordered.items()]


def _group_sum(dataframe: pd.DataFrame, group: str | None, metric: str | None, value_name: str, limit: int | None = None) -> list[dict[str, Any]]:
    if not group or not metric:
        return []
    return _records(dataframe.groupby(group, dropna=False)[metric].sum(), value_name, limit=limit)


def _group_average(dataframe: pd.DataFrame, group: str, metric: str) -> list[dict[str, Any]]:
    return _records(dataframe.groupby(group, dropna=False)[metric].mean(), f"average_{_field_name(metric)}")


def _group_count(dataframe: pd.DataFrame, group: str) -> list[dict[str, Any]]:
    return _records(dataframe.groupby(group, dropna=False).size(), "count")


def _is_identifier(column: str) -> bool:
    name = column.casefold().replace(" ", "")
    return name == "id" or name.endswith("id") or "number" in name or "code" in name


def _generic_numeric_columns(profile: DatasetProfile) -> list[str]:
    """Prefer useful measures over technical identifiers, with a small chart/KPI cap."""
    return [column for column in profile.numerical_columns if not _is_identifier(column)][:3]


def _generic_metrics(dataframe: pd.DataFrame, profile: DatasetProfile) -> dict[str, float]:
    employee_identifier = next((column for column in profile.column_names if "employee" in column.casefold() and _is_identifier(column)), None)
    metrics: dict[str, float] = {"employee_count" if employee_identifier else "record_count": float(profile.row_count)}
    for column in _generic_numeric_columns(profile):
        metrics[f"average_{_field_name(column)}"] = float(dataframe[column].mean())
    attrition = _column(dataframe, "Attrition")
    if attrition:
        values = dataframe[attrition].astype("string").str.casefold()
        metrics["attrition_rate"] = float(values.isin({"yes", "true", "1"}).mean() * 100)
    return metrics


def _sales_metrics(dataframe: pd.DataFrame, sales: str | None, profit: str | None, quantity: str | None) -> dict[str, float]:
    metrics: dict[str, float] = {}
    if sales:
        total_sales = float(dataframe[sales].sum())
        metrics.update(total_sales=total_sales, average_sales=float(dataframe[sales].mean()))
    else:
        total_sales = None
    if profit:
        total_profit = float(dataframe[profit].sum())
        metrics.update(total_profit=total_profit, average_profit=float(dataframe[profit].mean()))
    else:
        total_profit = None
    if quantity:
        metrics["total_quantity"] = float(dataframe[quantity].sum())
    if total_sales not in (None, 0) and total_profit is not None:
        metrics["profit_margin"] = total_profit / total_sales * 100
    return metrics


def _time_analysis(dataframe: pd.DataFrame, profile: DatasetProfile, sales: str | None, profit: str | None) -> dict[str, list[dict[str, Any]]]:
    if not profile.data_quality_issues.possible_date_columns:
        return {}
    date_column = profile.data_quality_issues.possible_date_columns[0]
    dates = pd.to_datetime(dataframe[date_column], errors="coerce", format="mixed")
    valid = dataframe.loc[dates.notna()].copy()
    if valid.empty:
        return {}
    valid["period"] = dates.loc[dates.notna()].dt.to_period("M").astype(str)
    results: dict[str, list[dict[str, Any]]] = {}
    if sales:
        results["sales_by_month"] = _records(valid.groupby("period")[sales].sum(), "sales")
    if profit:
        results["profit_by_month"] = _records(valid.groupby("period")[profit].sum(), "profit")
    return results


def analyze_dataframe(dataframe: pd.DataFrame, profile: DatasetProfile) -> EdaResults:
    """Build domain-aware EDA while retaining meaningful generic fallbacks."""
    sales, profit, quantity = (_column(dataframe, name) for name in ("Sales", "Profit", "Quantity"))
    region, category, segment, product = (_column(dataframe, name) for name in ("Region", "Category", "Segment", "Product Name"))
    is_sales_dataset = any((sales, profit, quantity))
    overall_metrics = _sales_metrics(dataframe, sales, profit, quantity) if is_sales_dataset else _generic_metrics(dataframe, profile)

    categorical: dict[str, list[dict[str, Any]]] = {}
    for key, group, metric, name, limit in (
        ("sales_by_region", region, sales, "sales", None), ("profit_by_region", region, profit, "profit", None),
        ("sales_by_category", category, sales, "sales", None), ("profit_by_category", category, profit, "profit", None),
        ("sales_by_segment", segment, sales, "sales", None), ("profit_by_segment", segment, profit, "profit", None),
        ("top_products_by_sales", product, sales, "sales", 10), ("top_products_by_profit", product, profit, "profit", 10),
    ):
        records = _group_sum(dataframe, group, metric, name, limit)
        if records:
            categorical[key] = records
    if product and profit:
        categorical["bottom_products_by_profit"] = _records(dataframe.groupby(product)[profit].sum(), "profit", ascending=True, limit=10)

    # Generic categories get counts and averages. Summing a measure such as
    # Age is not meaningful, so aggregation is deliberately semantic here.
    generic_categories = [
        column for column in profile.categorical_columns
        if column not in profile.data_quality_issues.possible_date_columns and 1 < profile.unique_value_counts[column] <= 20
    ]
    for group in generic_categories:
        group_key = _field_name(group)
        categorical.setdefault(f"count_by_{group_key}", _group_count(dataframe, group))
        if is_sales_dataset and sales:
            categorical.setdefault(f"sales_by_{group_key}", _group_sum(dataframe, group, sales, "sales"))
        else:
            for metric in _generic_numeric_columns(profile):
                categorical[f"average_{_field_name(metric)}_by_{group_key}"] = _group_average(dataframe, group, metric)

    numeric = dataframe[profile.numerical_columns]
    correlations = {str(row): {str(column): float(value) if pd.notna(value) else None for column, value in values.items()} for row, values in numeric.corr().to_dict().items()} if not numeric.empty else {}
    relationships = {
        "sales_vs_profit_correlation": correlations.get(sales, {}).get(profit) if sales and profit else None,
        "quantity_vs_sales_correlation": correlations.get(quantity, {}).get(sales) if quantity and sales else None,
    }
    relationship_data = {"sales_vs_profit": [{"sales": float(sales_value), "profit": float(profit_value)} for sales_value, profit_value in dataframe[[sales, profit]].dropna().head(500).itertuples(index=False, name=None)] if sales and profit else []}
    loss_making = [item for item in categorical.get("bottom_products_by_profit", []) if item["profit"] < 0]
    patterns = [f"{len(loss_making)} of the bottom ten products by profit are loss-making." if loss_making else "No loss-making products appear in the bottom ten products by profit."] if is_sales_dataset else [f"The dataset contains {profile.row_count} records and {profile.column_count} columns."]
    return EdaResults(overall_metrics=overall_metrics, categorical_analysis=categorical, time_analysis=_time_analysis(dataframe, profile, sales, profit), correlations=correlations, relationships=relationships, relationship_data=relationship_data, business_insights={"loss_making_products": loss_making, "potentially_important_patterns": patterns})


def analyze_dataset(source: str, profile: DatasetProfile) -> EdaResults:
    return analyze_dataframe(read_csv_with_fallback_encodings(source), profile)
