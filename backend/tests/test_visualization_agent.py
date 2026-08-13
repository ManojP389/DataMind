"""Tests for visualization specifications and graph-state propagation."""

import pandas as pd

from app.graph.workflow import build_dataset_analysis_workflow
from app.tools import data_tools
from app.tools.data_tools import profile_dataframe
from app.tools.eda_tools import analyze_dataframe
from app.tools.visualization_tools import build_visualizations, choose_chart_type


def _eda_result():
    dataframe = pd.DataFrame(
        {
            "Order Date": ["2024-01-10", "2024-02-10", "2024-02-20"],
            "Region": ["East", "West", "East"],
            "Category": ["Furniture", "Technology", "Furniture"],
            "Sales": [100.0, 300.0, 50.0],
            "Profit": [10.0, 60.0, -5.0],
        }
    )
    return analyze_dataframe(dataframe, profile_dataframe(dataframe))


def _city_sales_eda_result():
    dataframe = pd.DataFrame({"city": ["Delhi", "Mumbai"], "sales": [100.0, 200.0]})
    return analyze_dataframe(dataframe, profile_dataframe(dataframe))


def test_visualization_result_exists() -> None:
    charts = build_visualizations(_eda_result())

    assert charts
    assert {"chart_type", "title", "x_axis", "y_axis", "data"} == set(charts[0].model_dump())


def test_bar_chart_generation() -> None:
    chart = next(chart for chart in build_visualizations(_eda_result()) if chart.title == "Sales by Region")

    assert chart.chart_type == "bar"
    assert chart.data[0] == {"Region": "West", "sales": 300.0}


def test_line_chart_generation() -> None:
    chart = next(chart for chart in build_visualizations(_eda_result()) if chart.title == "Sales over Time")

    assert chart.chart_type == "line"
    assert chart.x_axis == "period"


def test_scatter_chart_generation() -> None:
    chart = next(chart for chart in build_visualizations(_eda_result()) if chart.title == "Sales vs Profit")

    assert chart.chart_type == "scatter"
    assert chart.x_axis == "sales"
    assert chart.y_axis == "profit"


def test_pie_chart_type_is_supported() -> None:
    assert choose_chart_type(analysis_kind="proportion", data=[{"category": "A", "sales": 1}]) == "pie"


def test_city_and_sales_generates_a_categorical_bar_chart_without_profit_or_dates() -> None:
    eda_results = _city_sales_eda_result()
    chart = next(chart for chart in build_visualizations(eda_results) if chart.title == "Sales by City")

    assert eda_results.time_analysis == {}
    assert chart.chart_type == "bar"
    assert chart.x_axis == "city"
    assert chart.y_axis == "sales"
    assert chart.data == [{"city": "Mumbai", "sales": 200.0}, {"city": "Delhi", "sales": 100.0}]


def test_hr_style_data_generates_dataset_aware_charts() -> None:
    dataframe = pd.DataFrame({
        "EmployeeNumber": [1, 2, 3, 4], "Age": [30, 40, 20, 50], "MonthlyIncome": [3000, 5000, 2000, 7000],
        "Attrition": ["No", "Yes", "No", "Yes"], "Department": ["Sales", "HR", "Sales", "HR"],
        "BusinessTravel": ["Travel_Rarely", "Travel_Frequently", "Travel_Rarely", "Non-Travel"], "EducationField": ["Life Sciences", "Medical", "Medical", "Life Sciences"],
    })
    charts = build_visualizations(analyze_dataframe(dataframe, profile_dataframe(dataframe)))
    by_title = {chart.title: chart for chart in charts}

    assert by_title["Attrition Distribution"].chart_type == "pie"
    assert by_title["Average Age by Attrition"].y_axis == "average_age"
    assert "Record Count by Department" in by_title


def test_dataset_without_categorical_columns_omits_unsupported_charts() -> None:
    dataframe = pd.DataFrame({"Temperature": [18.0, 20.0], "Humidity": [55.0, 60.0]})
    assert build_visualizations(analyze_dataframe(dataframe, profile_dataframe(dataframe))) == []


def test_visualization_state_propagation(tmp_path, monkeypatch) -> None:
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    file_id = "a" * 32
    (uploads / f"{file_id}.csv").write_bytes(b"Region,Category,Sales,Profit\nEast,Furniture,100,10\nWest,Technology,200,20\n")
    monkeypatch.setattr(data_tools, "UPLOADS_DIRECTORY", uploads)

    state = build_dataset_analysis_workflow().invoke({"file_id": file_id, "user_request": "Analyze", "current_agent": "", "execution": []})

    assert state["visualization_results"]
    assert state["execution"][-1] == {"agent": "visualization_agent", "event": "visualizations_created"}
