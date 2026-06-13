from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class DiagnoseRequest(BaseModel):
    service_name: str = Field(..., description="The name of the service to diagnose (e.g. payment-service)")

class PodInfo(BaseModel):
    name: str
    status: str
    restart_count: int
    ready: str
    ip: str
    node: str
    created_at: str

class PodStatus(BaseModel):
    service: str
    pods: List[PodInfo]

class DiagnoseResponse(BaseModel):
    service_name: str
    pod_status: Dict[str, Any]
    log_analysis: str
    metrics_analysis: str
    runbook_matched: bool
    root_cause: str
    recommendations: str
    confidence_score: float

class ExplainErrorRequest(BaseModel):
    error_message: str = Field(..., description="The error message or stack trace to explain")

class ExplainErrorResponse(BaseModel):
    explanation: str
    potential_causes: List[str]
    remediation_steps: List[str]

class SearchDocsRequest(BaseModel):
    query: str = Field(..., description="The query to search in runbooks")
    limit: Optional[int] = Field(3, description="Maximum number of search results to return")

class SearchResult(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any]
    distance: float

class SearchDocsResponse(BaseModel):
    results: List[SearchResult]

class AskRequest(BaseModel):
    question: str = Field(..., description="General SRE question to ask the Copilot")

class AskResponse(BaseModel):
    answer: str
    sources: List[str]

class HealthResponse(BaseModel):
    status: str
    chromadb: str
    api_key_configured: bool
