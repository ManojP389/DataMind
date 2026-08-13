"""Tests for the first DataMind LangGraph workflow."""

from app.agents.manager_agent import ManagerAgent
from app.graph.workflow import build_dataset_analysis_workflow, manager_node
from app.tools import data_tools


def test_graph_initialization() -> None:
    workflow = build_dataset_analysis_workflow()

    assert workflow is not None


def test_manager_routes_to_data_agent() -> None:
    result = ManagerAgent().route_dataset_analysis(
        {
            "file_id": "a" * 32,
            "user_request": "Profile this dataset.",
            "current_agent": "manager",
            "execution": [],
        }
    )

    assert result["current_agent"] == "data_agent"
    assert result["execution"] == [{"agent": "manager", "event": "routed_to_data_agent"}]
    assert manager_node({"file_id": "a" * 32, "user_request": "Profile", "current_agent": "", "execution": []}) == result | {"execution": result["execution"]}


def test_graph_execution_returns_dataset_profile(tmp_path, monkeypatch) -> None:
    upload_directory = tmp_path / "uploads"
    upload_directory.mkdir()
    file_id = "c" * 32
    (upload_directory / f"{file_id}.csv").write_bytes(b"region,sales\nNorth,100\nSouth,200\n")
    monkeypatch.setattr(data_tools, "UPLOADS_DIRECTORY", upload_directory)

    final_state = build_dataset_analysis_workflow().invoke(
        {
            "file_id": file_id,
            "user_request": "Analyze this dataset.",
            "current_agent": "",
            "execution": [],
        }
    )

    assert final_state["dataset_profile"].row_count == 2
    assert final_state["dataset_profile"].column_names == ["region", "sales"]
    assert final_state["current_agent"] == "visualization_agent"
    assert final_state["eda_results"]
    assert final_state["visualization_results"]
    assert final_state["eda_results"].overall_metrics["total_sales"] == 300.0
    assert final_state["execution"] == [
        {"agent": "manager", "event": "routed_to_data_agent"},
        {"agent": "data_agent", "event": "profile_completed"},
        {"agent": "data_agent", "event": "routed_to_eda_agent"},
        {"agent": "eda_agent", "event": "analysis_completed"},
        {"agent": "visualization_agent", "event": "visualizations_created"},
    ]
