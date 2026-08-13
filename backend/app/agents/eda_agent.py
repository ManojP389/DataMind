"""EDA Agent, designed as the second worker in the DataMind graph."""

from pathlib import Path

from app.models.data_profile import DatasetProfile, EdaResults
from app.tools.eda_tools import analyze_dataset


class EdaAgent:
    """Run structured Pandas-only exploratory analysis on a profiled dataset."""

    def analyze(self, source: str | Path, dataset_profile: DatasetProfile) -> EdaResults:
        return analyze_dataset(str(source), dataset_profile)
