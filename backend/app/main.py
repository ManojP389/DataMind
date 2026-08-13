"""FastAPI application entry point."""

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, status

from app.agents.data_agent import DataProfilingAgent
from app.graph.workflow import dataset_analysis_workflow, query_workflow
from app.models.data_profile import AgentAnalysisResponse, AgentQueryResponse, DatasetProfile
from app.models.dataset import DatasetUploadResponse
from app.services.upload_service import InvalidDatasetError, process_csv_upload
from app.tools.data_tools import FILE_ID_PATTERN, resolve_dataset_source


app = FastAPI(title="DataMind", version="0.1.0")
data_profiling_agent = DataProfilingAgent()


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Report whether the API service is available."""
    return {"status": "ok", "service": "DataMind"}


@app.post("/upload", response_model=DatasetUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(file: UploadFile = File(...)) -> DatasetUploadResponse:
    """Store and profile a CSV dataset upload."""
    try:
        return await process_csv_upload(file)
    except InvalidDatasetError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from error


@app.post("/analyze/{file_id}", response_model=DatasetProfile)
def analyze_dataset(file_id: str) -> DatasetProfile:
    """Return the existing Data Profiling Agent's profile for an upload."""
    if not FILE_ID_PATTERN.fullmatch(file_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset file was not found.")

    try:
        return data_profiling_agent.profile(file_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset file was not found.") from error
    except (ValueError, OSError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Dataset could not be analyzed.") from error


@app.post("/agent/analyze/{file_id}", response_model=AgentAnalysisResponse)
def analyze_dataset_with_agents(
    file_id: str,
    user_request: str = Query(default="Analyze this dataset."),
) -> AgentAnalysisResponse:
    """Run the Manager → Data Agent LangGraph workflow for an uploaded CSV."""
    if not FILE_ID_PATTERN.fullmatch(file_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset file was not found.")

    try:
        resolve_dataset_source(file_id)
        final_state = dataset_analysis_workflow.invoke(
            {
                "file_id": file_id,
                "user_request": user_request,
                "dataset_profile": None,
                "eda_results": None,
                "visualization_results": [],
                "current_agent": "",
                "execution": [],
                "run_sql": False,
            }
        )
        return AgentAnalysisResponse(
            dataset_profile=final_state["dataset_profile"],
            eda_results=final_state["eda_results"],
            visualization_results=final_state["visualization_results"],
            execution=final_state["execution"],
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset file was not found.") from error
    except (ValueError, OSError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Dataset could not be analyzed.") from error


@app.post("/agent/query/{file_id}", response_model=AgentQueryResponse | AgentAnalysisResponse)
def query_dataset_with_agents(file_id: str, user_request: str = Query(..., min_length=1)) -> AgentQueryResponse | AgentAnalysisResponse:
    """Run Ask DataMind through the Manager's validated query or analysis route."""
    if not FILE_ID_PATTERN.fullmatch(file_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset file was not found.")
    try:
        resolve_dataset_source(file_id)
        final_state = query_workflow.invoke(
            {
                "file_id": file_id,
                "user_request": user_request,
                "dataset_profile": None,
                "eda_results": None,
                "sql_query": None,
                "sql_result": None,
                "insight": None,
                "intent": None,
                "visualization_results": [],
                "current_agent": "",
                "execution": [],
                "run_sql": False,
            }
        )
        if final_state["intent"] == "analysis":
            return AgentAnalysisResponse(
                dataset_profile=final_state["dataset_profile"],
                eda_results=final_state["eda_results"],
                visualization_results=final_state["visualization_results"],
                execution=final_state["execution"],
            )
        return AgentQueryResponse(
            sql_result=final_state["sql_result"],
            insight=final_state["insight"],
            visualization_results=final_state.get("visualization_results", []),
            execution=final_state["execution"],
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset file was not found.") from error
    except (ValueError, OSError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
