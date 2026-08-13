"""Data Profiling Agent, designed to become a future LangGraph node."""

from pathlib import Path

from app.models.data_profile import DatasetProfile
from app.tools.data_tools import profile_dataframe, read_csv_with_fallback_encodings


class DataProfilingAgent:
    """Load a CSV dataset and return a deterministic Pandas profile."""

    def profile(self, source: str | Path) -> DatasetProfile:
        dataframe = read_csv_with_fallback_encodings(source)
        return profile_dataframe(dataframe)
