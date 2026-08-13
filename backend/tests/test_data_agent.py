"""Unit tests for the Pandas-based Data Profiling Agent."""

import pandas as pd

from app.tools.data_tools import profile_dataframe


def test_profile_dataframe_reports_statistics_and_quality_issues() -> None:
    dataframe = pd.DataFrame(
        {
            "age": [25, 25, None, 25],
            "city": ["Delhi", "Delhi", "Delhi", "Delhi"],
            "joined_on": ["2024-01-01", "2024-01-01", None, "2024-01-01"],
            "amount": ["10", "10", "30", "10"],
        }
    )

    profile = profile_dataframe(dataframe)

    assert profile.row_count == 4
    assert profile.column_count == 4
    assert profile.numerical_columns == ["age"]
    assert profile.categorical_columns == ["city", "joined_on", "amount"]
    assert profile.missing_value_counts == {"age": 1, "city": 0, "joined_on": 1, "amount": 0}
    assert profile.missing_value_percentages["age"] == 25.0
    assert profile.duplicate_row_count == 2
    assert profile.unique_value_counts["city"] == 1
    assert profile.numerical_descriptive_statistics["age"]["count"] == 3.0
    assert profile.data_quality_issues.missing_value_columns == ["age", "joined_on"]
    assert profile.data_quality_issues.duplicate_row_count == 2
    assert profile.data_quality_issues.single_value_columns == ["age", "city", "joined_on"]
    assert profile.data_quality_issues.possible_date_columns == ["joined_on"]
    assert profile.data_quality_issues.numeric_string_columns == ["amount"]
