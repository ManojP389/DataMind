"""Manager Agent for deterministic analysis and LLM-classified query workflows."""

from __future__ import annotations

import json

from app.graph.state import DataMindGraphState, WorkflowExecution
from app.services.llm_service import GroqSqlService, IntentClassificationService


class ManagerAgent:
    """Route known analysis work and classify Ask DataMind requests safely."""

    def __init__(self, llm_service: IntentClassificationService | None = None) -> None:
        self.llm_service = llm_service or GroqSqlService()

    def route_dataset_analysis(self, state: DataMindGraphState) -> dict[str, object]:
        """Select Data Agent as the first worker in this limited workflow."""
        execution: list[WorkflowExecution] = [
            *state.get("execution", []),
            {"agent": "manager", "event": "routed_to_data_agent"},
        ]
        return {"current_agent": "data_agent", "execution": execution}

    def classify_query_request(self, state: DataMindGraphState) -> dict[str, object]:
        """Classify an Ask request while keeping graph routing independent of raw LLM text."""
        intent = self._classify_intent(state["user_request"])
        execution: list[WorkflowExecution] = [
            *state.get("execution", []),
            {"agent": "manager", "event": "classified_request", "intent": intent},
        ]
        return {"intent": intent, "current_agent": "manager", "execution": execution}

    def _classify_intent(self, user_request: str) -> str:
        """Validate model JSON and use a safe deterministic fallback on any failure."""
        try:
            response = self.llm_service.generate_intent(user_request)
            parsed = json.loads(response)
            if isinstance(parsed, dict) and set(parsed) == {"intent"} and parsed["intent"] in {"query", "analysis"}:
                return parsed["intent"]
        except Exception:
            pass
        return self._fallback_intent(user_request)

    @staticmethod
    def _fallback_intent(user_request: str) -> str:
        """Classify clear analysis requests locally; default safely to a data query."""
        normalized = user_request.lower()
        analysis_terms = ("analyze", "analyse", "overview", "summarize", "summary", "profile")
        return "analysis" if any(term in normalized for term in analysis_terms) else "query"
