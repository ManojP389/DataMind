"""Unit tests for Pandas-only EDA calculations."""

import pandas as pd

from app.tools.data_tools import profile_dataframe
from app.tools.eda_tools import analyze_dataframe


def sample_sales_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Order Date": ["2024-01-10", "2024-02-10", "2024-02-20"],
            "Region": ["East", "West", "East"],
            "Category": ["Furniture", "Technology", "Furniture"],
            "Segment": ["Consumer", "Corporate", "Consumer"],
            "Product Name": ["Desk", "Laptop", "Chair"],
            "Sales": [100.0, 300.0, 50.0],
            "Profit": [10.0, 60.0, -5.0],
            "Quantity": [1, 2, 1],
        }
    )


def test_eda_calculates_overall_sales_and_profit() -> None:
    dataframe = sample_sales_dataframe()
    result = analyze_dataframe(dataframe, profile_dataframe(dataframe))

    assert result.overall_metrics["total_sales"] == 450.0
    assert result.overall_metrics["total_profit"] == 65.0
    assert result.overall_metrics["total_quantity"] == 4.0


def test_eda_groups_categories_regions_and_products() -> None:
    dataframe = sample_sales_dataframe()
    result = analyze_dataframe(dataframe, profile_dataframe(dataframe))

    assert result.categorical_analysis["sales_by_category"][0] == {"Category": "Technology", "sales": 300.0}
    assert result.categorical_analysis["profit_by_region"][0] == {"Region": "West", "profit": 60.0}
    assert result.categorical_analysis["top_products_by_sales"][0] == {"Product Name": "Laptop", "sales": 300.0}
    assert result.categorical_analysis["bottom_products_by_profit"][0] == {"Product Name": "Chair", "profit": -5.0}


def test_eda_performs_date_analysis() -> None:
    dataframe = sample_sales_dataframe()
    result = analyze_dataframe(dataframe, profile_dataframe(dataframe))

    assert result.time_analysis["sales_by_month"] == [
        {"period": "2024-02", "sales": 350.0},
        {"period": "2024-01", "sales": 100.0},
    ]


def test_eda_uses_generic_average_and_count_metrics_for_hr_style_data() -> None:
    dataframe = pd.DataFrame({
        "EmployeeNumber": [1, 2, 3, 4], "Age": [30, 40, 20, 50], "MonthlyIncome": [3000, 5000, 2000, 7000],
        "YearsAtCompany": [2, 8, 1, 12], "Attrition": ["No", "Yes", "No", "Yes"],
        "Department": ["Sales", "HR", "Sales", "HR"], "BusinessTravel": ["Travel_Rarely", "Travel_Frequently", "Travel_Rarely", "Non-Travel"],
    })
    result = analyze_dataframe(dataframe, profile_dataframe(dataframe))

    assert result.overall_metrics == {"employee_count": 4.0, "average_age": 35.0, "average_monthlyincome": 4250.0, "average_yearsatcompany": 5.75, "attrition_rate": 50.0}
    assert result.categorical_analysis["average_age_by_attrition"] == [{"Attrition": "Yes", "average_age": 45.0}, {"Attrition": "No", "average_age": 25.0}]
    assert result.categorical_analysis["count_by_department"] == [{"Department": "HR", "count": 2.0}, {"Department": "Sales", "count": 2.0}]


def test_eda_without_sales_or_numerical_columns_does_not_emit_sales_metrics() -> None:
    dataframe = pd.DataFrame({"Status": ["Open", "Closed"], "Team": ["A", "B"]})
    result = analyze_dataframe(dataframe, profile_dataframe(dataframe))

    assert result.overall_metrics == {"record_count": 2.0}
    assert "count_by_status" in result.categorical_analysis


def test_eda_without_categorical_columns_returns_generic_kpis_without_category_charts() -> None:
    dataframe = pd.DataFrame({"Temperature": [18.0, 20.0], "Humidity": [55.0, 60.0]})
    result = analyze_dataframe(dataframe, profile_dataframe(dataframe))

    assert result.overall_metrics["average_temperature"] == 19.0
    assert result.categorical_analysis == {}
