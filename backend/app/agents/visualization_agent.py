"""Visualization Agent that converts existing analysis into chart specifications."""

from app.models.data_profile import ChartSpecification, EdaResults
from app.models.sql_result import SqlResult
from app.tools.visualization_tools import build_visualizations


class VisualizationAgent:
    """Create chart specs without loading datasets or recalculating statistics."""

    def create(self, eda_results: EdaResults, sql_result: SqlResult | None = None) -> list[ChartSpecification]:
        return build_visualizations(eda_results, sql_result)
