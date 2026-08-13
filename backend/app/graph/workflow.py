"""First DataMind workflow: Manager Agent routes to Data Profiling Agent."""

from langgraph.graph import END, START, StateGraph

from app.agents.data_agent import DataProfilingAgent
from app.agents.eda_agent import EdaAgent
from app.agents.insight_agent import InsightAgent
from app.agents.manager_agent import ManagerAgent
from app.agents.sql_agent import SqlAgent
from app.agents.visualization_agent import VisualizationAgent
from app.graph.state import DataMindGraphState, WorkflowExecution


manager_agent = ManagerAgent()
data_profiling_agent = DataProfilingAgent()
eda_agent = EdaAgent()
sql_agent = SqlAgent()
insight_agent = InsightAgent()
visualization_agent = VisualizationAgent()


def manager_node(state: DataMindGraphState) -> dict[str, object]:
    """Route a dataset-analysis request to its first worker."""
    return manager_agent.route_dataset_analysis(state)


def query_manager_node(state: DataMindGraphState) -> dict[str, object]:
    """Classify an Ask DataMind request before conditional routing."""
    return manager_agent.classify_query_request(state)


def data_agent_node(state: DataMindGraphState) -> dict[str, object]:
    """Run the existing Pandas-based profiling agent for the uploaded dataset."""
    execution: list[WorkflowExecution] = [
        *state.get("execution", []),
        {"agent": "data_agent", "event": "profile_completed"},
        {"agent": "data_agent", "event": "routed_to_eda_agent"},
    ]
    return {
        "dataset_profile": data_profiling_agent.profile(state["file_id"]),
        "current_agent": "data_agent",
        "execution": execution,
    }


def eda_agent_node(state: DataMindGraphState) -> dict[str, object]:
    """Run EDA using the Data Agent's already-computed dataset profile."""
    execution: list[WorkflowExecution] = [
        *state.get("execution", []),
        {"agent": "eda_agent", "event": "analysis_completed"},
    ]
    if state.get("run_sql", False):
        execution.append({"agent": "eda_agent", "event": "routed_to_sql_agent"})
    dataset_profile = state.get("dataset_profile")
    if dataset_profile is None:
        raise ValueError("EDA requires a dataset profile from the Data Agent.")
    return {
        "eda_results": eda_agent.analyze(state["file_id"], dataset_profile),
        "current_agent": "eda_agent",
        "execution": execution,
    }


def sql_agent_node(state: DataMindGraphState) -> dict[str, object]:
    """Run the SQL Agent for explicit graph-backed query requests."""
    sql_result = sql_agent.query(state["file_id"], state["user_request"])
    execution: list[WorkflowExecution] = [
        *state.get("execution", []),
        {"agent": "sql_agent", "event": "query_completed"},
        {"agent": "sql_agent", "event": "routed_to_insight_agent"},
    ]
    return {
        "sql_query": sql_result.sql,
        "sql_result": sql_result,
        "current_agent": "sql_agent",
        "execution": execution,
    }


def insight_agent_node(state: DataMindGraphState) -> dict[str, object]:
    """Generate an explanation from an already-executed SQL result."""
    sql_result = state.get("sql_result")
    if sql_result is None:
        raise ValueError("Insight generation requires a SQL result.")
    execution: list[WorkflowExecution] = [
        *state.get("execution", []),
        {"agent": "insight_agent", "event": "insight_generated"},
    ]
    return {
        "insight": insight_agent.generate(
            sql_result.question, sql_result.sql, sql_result.columns, sql_result.rows
        ),
        "current_agent": "insight_agent",
        "execution": execution,
    }


def visualization_agent_node(state: DataMindGraphState) -> dict[str, object]:
    """Create chart specifications from EDA and optional SQL state only."""
    eda_results = state.get("eda_results")
    if eda_results is None:
        raise ValueError("Visualization requires EDA results from the EDA Agent.")
    execution: list[WorkflowExecution] = [
        *state.get("execution", []),
        {"agent": "visualization_agent", "event": "visualizations_created"},
    ]
    return {
        "visualization_results": visualization_agent.create(eda_results, state.get("sql_result")),
        "current_agent": "visualization_agent",
        "execution": execution,
    }


def route_after_eda(state: DataMindGraphState) -> str:
    """Run SQL only for query requests; all paths finish with visualizations."""
    return "sql_agent" if state.get("run_sql", False) else "visualization_agent"


def route_after_query_manager(state: DataMindGraphState) -> str:
    """Route only validated manager intents; unknown values take the analysis path."""
    return "sql_agent" if state.get("intent") == "query" else "data_agent"


def build_dataset_analysis_workflow():
    """Build the deterministic START → Manager → Data Agent → END graph."""
    workflow = StateGraph(DataMindGraphState)
    workflow.add_node("manager", manager_node)
    workflow.add_node("data_agent", data_agent_node)
    workflow.add_node("eda_agent", eda_agent_node)
    workflow.add_node("sql_agent", sql_agent_node)
    workflow.add_node("insight_agent", insight_agent_node)
    workflow.add_node("visualization_agent", visualization_agent_node)
    workflow.add_edge(START, "manager")
    workflow.add_edge("manager", "data_agent")
    workflow.add_edge("data_agent", "eda_agent")
    workflow.add_conditional_edges("eda_agent", route_after_eda, {"sql_agent": "sql_agent", "visualization_agent": "visualization_agent"})
    workflow.add_edge("sql_agent", "insight_agent")
    workflow.add_edge("insight_agent", END)
    workflow.add_edge("visualization_agent", END)
    return workflow.compile()


def build_query_workflow():
    """Build Ask DataMind's Manager-routed query and analysis workflow."""
    workflow = StateGraph(DataMindGraphState)
    workflow.add_node("manager", query_manager_node)
    workflow.add_node("data_agent", data_agent_node)
    workflow.add_node("eda_agent", eda_agent_node)
    workflow.add_node("sql_agent", sql_agent_node)
    workflow.add_node("insight_agent", insight_agent_node)
    workflow.add_node("visualization_agent", visualization_agent_node)
    workflow.add_edge(START, "manager")
    workflow.add_conditional_edges(
        "manager",
        route_after_query_manager,
        {"sql_agent": "sql_agent", "data_agent": "data_agent"},
    )
    workflow.add_edge("data_agent", "eda_agent")
    workflow.add_edge("eda_agent", "visualization_agent")
    workflow.add_edge("sql_agent", "insight_agent")
    workflow.add_edge("insight_agent", END)
    workflow.add_edge("visualization_agent", END)
    return workflow.compile()


dataset_analysis_workflow = build_dataset_analysis_workflow()
query_workflow = build_query_workflow()
