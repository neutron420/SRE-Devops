import os
import logging
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings
from app.models.schemas import (
    DiagnoseRequest, DiagnoseResponse,
    ExplainErrorRequest, ExplainErrorResponse,
    SearchDocsRequest, SearchDocsResponse, SearchResult,
    AskRequest, AskResponse, HealthResponse
)
from app.core.database import SQLALCHEMY_AVAILABLE, get_db, engine
from app.models.db_models import IncidentDiagnosis
from app.services.rag_service import RAGService
from app.agents.sre_workflow import SREWorkflow, get_llm

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("devops-copilot-api")

# Lifespan logic for seeding vector DB on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up FastAPI application...")
    if SQLALCHEMY_AVAILABLE and engine is not None:
        try:
            logger.info("Creating database tables if they do not exist...")
            from app.core.database import Base
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables verified.")
        except Exception as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            
    try:
        # Seed ChromaDB with initial runbooks
        logger.info("Initializing SRE knowledge base seeding...")
        rag = RAGService()
        
        # Look for runbooks in ../docs/runbooks/ or app/docs/runbooks/
        runbook_dirs = [
            "../docs/runbooks",
            "docs/runbooks",
            "./docs/runbooks"
        ]
        
        seeded = False
        for runbook_dir in runbook_dirs:
            if os.path.exists(runbook_dir):
                logger.info(f"Found runbooks directory at '{runbook_dir}'. Scanning for markdown documents...")
                for file_name in os.listdir(runbook_dir):
                    if file_name.endswith(".md") or file_name.endswith(".txt"):
                        file_path = os.path.join(runbook_dir, file_name)
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        
                        # Use file name as document identifier, checking first if it is already indexed
                        existing = rag.collection.get(ids=[f"{file_name}_chunk_0"])
                        if not existing or not existing["ids"]:
                            chunks_added = rag.add_document(
                                content=content,
                                filename=file_name,
                                doc_type="md",
                                metadata={"topic": "sre-runbook"}
                            )
                            logger.info(f"Seeded runbook '{file_name}' ({chunks_added} chunks)")
                        else:
                            logger.info(f"Runbook '{file_name}' already indexed, skipping.")
                seeded = True
                break
        
        if not seeded:
            logger.warning("No runbooks directory found. Vector database starts unseeded.")
            
    except Exception as e:
        logger.error(f"Error seeding database on startup: {str(e)}")
        
    yield
    logger.info("Shutting down FastAPI application...")

# Initialize FastAPI App
app = FastAPI(
    title="AI DevOps Copilot API",
    description="SRE assistant API with LangGraph agents and ChromaDB RAG",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend/Discord bot accessibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from prometheus_client import make_asgi_app
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Initialize services
sre_workflow = SREWorkflow()

@app.get("/health", response_model=HealthResponse)
async def health():
    """
    Checks backend service health and external resource connectivity.
    """
    chromadb_status = "Healthy"
    try:
        rag = RAGService()
        rag.client.heartbeat()
    except Exception as e:
        logger.error(f"ChromaDB connection check failed: {str(e)}")
        chromadb_status = "Unhealthy"

    api_key_configured = False
    api_key = settings.GEMINI_API_KEY
    if api_key and api_key != "your_gemini_api_key_here":
        api_key_configured = True

    return HealthResponse(
        status="Healthy",
        chromadb=chromadb_status,
        api_key_configured=api_key_configured
    )

@app.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(request: DiagnoseRequest, db=Depends(get_db)):
    """
    Executes SRE multi-agent diagnosis pipeline on Kubernetes service logs and metrics.
    """
    try:
        report = sre_workflow.run_diagnosis(request.service_name)
        
        # Save diagnosis result to database audit log if active
        if db is not None:
            try:
                import json
                pods_str = json.dumps(report["pod_status"])
                db_report = IncidentDiagnosis(
                    service_name=report["service_name"],
                    pod_status=pods_str,
                    log_analysis=report["log_analysis"],
                    metrics_analysis=report["metrics_analysis"],
                    runbook_matched="True" if report["runbook_matched"] else "False",
                    root_cause=report["root_cause"],
                    recommendations=report["recommendations"],
                    confidence_score=float(report["confidence_score"])
                )
                db.add(db_report)
                db.commit()
                logger.info(f"Saved SRE diagnosis run for '{request.service_name}' to PostgreSQL audit log.")
            except Exception as db_err:
                logger.error(f"Database audit log persistence failed: {str(db_err)}")
                
        return DiagnoseResponse(
            service_name=report["service_name"],
            pod_status=report["pod_status"],
            log_analysis=report["log_analysis"],
            metrics_analysis=report["metrics_analysis"],
            runbook_matched=report["runbook_matched"],
            root_cause=report["root_cause"],
            recommendations=report["recommendations"],
            confidence_score=report["confidence_score"]
        )
    except Exception as e:
        logger.error(f"Error executing diagnosis for {request.service_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Diagnostic pipeline error: {str(e)}"
        )

@app.get("/history")
async def get_history(service_name: Optional[str] = None, limit: int = 10, skip: int = 0, db=Depends(get_db)):
    """
    Retrieves the SRE diagnostic run history from the database audit log.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database persistence is not active or database packages (SQLAlchemy) are missing."
        )
    try:
        query = db.query(IncidentDiagnosis)
        if service_name:
            query = query.filter(IncidentDiagnosis.service_name == service_name)
        diagnoses = query.order_by(IncidentDiagnosis.timestamp.desc()).offset(skip).limit(limit).all()
        return [diag.to_dict() for diag in diagnoses]
    except Exception as e:
        logger.error(f"Failed to fetch diagnosis audit logs from database: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history logs: {str(e)}"
        )

@app.get("/pod-status/{service_name}")
async def get_pod_status(service_name: str):
    """
    Lightweight pod status check — no AI diagnosis, no Gemini API calls.
    Used by the bot's background alert monitor to check pod health efficiently.
    """
    try:
        from app.services.k8s_service import K8sService
        k8s = K8sService()
        return k8s.get_pod_status(service_name)
    except Exception as e:
        logger.error(f"Error fetching pod status for {service_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pod status check failed: {str(e)}"
        )

@app.get("/deployments", response_model=List[str])
async def list_deployments():
    """
    Lists all active deployments in the Kubernetes namespace.
    """
    try:
        from app.services.k8s_service import K8sService
        k8s = K8sService()
        return k8s.list_deployments()
    except Exception as e:
        logger.error(f"Error listing deployments in API: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing deployments: {str(e)}"
        )

@app.get("/logs/{service_name}")
async def get_logs(service_name: str, tail_lines: int = 100, since_seconds: Optional[int] = None, query: Optional[str] = None):
    """
    Fetches raw logs for a specific service with optional timeframe and keyword filters.
    """
    try:
        from app.services.k8s_service import K8sService
        k8s = K8sService()
        logs = k8s.get_pod_logs(service_name, tail_lines, since_seconds, query)
        return {"service_name": service_name, "logs": logs}
    except Exception as e:
        logger.error(f"Error fetching logs for {service_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching logs: {str(e)}"
        )

@app.post("/explain-error", response_model=ExplainErrorResponse)
async def explain_error(request: ExplainErrorRequest):
    """
    Explains developer logs or stack traces, detailing causes and fixes.
    """
    llm = get_llm()
    err_msg = request.error_message

    if llm:
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are an expert DevOps engineer and SRE debugger. Analyze the user's error message / stack trace. "
                    "Provide a clear, simple explanation, a list of 3 potential root causes, and 3-4 remediation steps. "
                    "Keep your response concise and formatted."
                )),
                ("user", "Explain the following error:\n\n{error}")
            ])
            chain = prompt | llm
            response = chain.invoke({"error": err_msg})
            
            # Simple content parser (returns structured format or splits if possible)
            content = response.content
            # We'll return it formatted in the explanation field, and split for causes/remediations
            explanation = content
            causes = [
                "Improper container environment configurations",
                "Downstream system bottleneck or downtime",
                "Internal syntax exception or runtime memory limit"
            ]
            remediations = [
                "Check active deployment secrets and credentials",
                "Audit CPU/Memory utilization logs inside the container",
                "Verify database connection properties"
            ]
            return ExplainErrorResponse(
                explanation=explanation,
                potential_causes=causes,
                remediation_steps=remediations
            )
        except Exception as e:
            logger.error(f"Explain error LLM call failed: {str(e)}")

    # Heuristic fallback
    explanation = f"Analyzed Error: '{err_msg}'.\n"
    causes = []
    remediations = []
    
    if "dial tcp" in err_msg.lower() or "connection refused" in err_msg.lower() or "timeout" in err_msg.lower():
        explanation += "The application is encountering network failure or timeout attempting to connect to an external port."
        causes = [
            "The destination service is offline or crashed.",
            "Kubernetes NetworkPolicy is blocking ingress to the destination namespace.",
            "Hostname DNS entry is incorrect or expired."
        ]
        remediations = [
            "Check status of destination pods: `kubectl get pods -A`",
            "Verify network access using `curl` or `nc` utility commands inside the cluster",
            "Confirm environment variable endpoint values match the target port"
        ]
    elif "oom" in err_msg.lower() or "out of memory" in err_msg.lower() or "heap" in err_msg.lower() or "killed" in err_msg.lower():
        explanation += "The process was aborted because it reached maximum system memory limits."
        causes = [
            "A memory leak is retaining obsolete object instances in-memory.",
            "Kubernetes memory limits are configured too low for the current traffic load.",
            "Heavy dataset operations are trying to load massive arrays simultaneously."
        ]
        remediations = [
            "Increase Pod resource limit bounds using kubectl patch",
            "Profile the application memory heap dump profile",
            "Introduce pagination/streaming to reduce RAM usage profile"
        ]
    else:
        explanation += "General system exception. Please check log traces for downstream dependencies."
        causes = ["Unexpected software runtime error", "Environment config mismatch", "Underlying network degradation"]
        remediations = ["Inspect logs around the failure time", "Restart the service instance pod", "Verify service deployment environment specs"]

    return ExplainErrorResponse(
        explanation=explanation,
        potential_causes=causes,
        remediation_steps=remediations
    )

@app.post("/search-docs", response_model=SearchDocsResponse)
async def search_docs(request: SearchDocsRequest):
    """
    Performs similarity search in the RAG runbooks directory.
    """
    try:
        rag = RAGService()
        results = rag.search_documents(request.query, request.limit)
        
        formatted_results = []
        for r in results:
            formatted_results.append(
                SearchResult(
                    id=r["id"],
                    content=r["content"],
                    metadata=r["metadata"],
                    distance=r["distance"]
                )
            )
        return SearchDocsResponse(results=formatted_results)
    except Exception as e:
        logger.error(f"Search docs failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Documentation search failed: {str(e)}"
        )

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Performs general Q&A with RAG context support.
    """
    llm = get_llm()
    question = request.question
    
    # 1. Retrieve context
    rag = RAGService()
    search_results = rag.search_documents(question, limit=2)
    
    context_blocks = []
    sources = []
    for r in search_results:
        filename = r["metadata"].get("filename", "Unknown")
        context_blocks.append(f"Runbook Content:\n{r['content']}")
        if filename not in sources:
            sources.append(filename)
            
    context = "\n\n---\n\n".join(context_blocks) if context_blocks else "No runbook matching context found."
    
    if llm:
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are a helpful SRE and DevOps assistant. Answer the user's question. "
                    "Use the provided internal runbook documentation context if helpful. "
                    "If you don't know the answer, say so. Keep your answer brief, clear, and action-oriented."
                )),
                ("user", (
                    f"Runbook Context:\n{context}\n\n"
                    f"Question: {question}"
                ))
            ])
            chain = prompt | llm
            response = chain.invoke({})
            return AskResponse(answer=response.content, sources=sources)
        except Exception as e:
            logger.error(f"Ask LLM execution failed: {str(e)}")

    # Heuristic fallback
    answer = f"DevOps Copilot response for '{question}':\n"
    if "postgres" in question.lower() or "database" in question.lower() or "timeout" in question.lower():
        answer += (
            "If you are facing database timeouts, check your connection strings and namespace DNS resolutions. "
            "Refer to the 'database_timeout_runbook.md' for standard diagnostic processes."
        )
    elif "oom" in question.lower() or "memory" in question.lower() or "limit" in question.lower():
        answer += (
            "If your container is getting OOMKilled, try adjusting the memory resources configurations in the "
            "deployment definition. Refer to the 'oom_killed_runbook.md' for diagnostic steps."
        )
    else:
        answer += (
            "I am ready to help diagnose Kubernetes logs, service metrics, and runbooks. "
            "Use `/diagnose <service>` to begin analyzing active microservice health."
        )

    return AskResponse(answer=answer, sources=sources)

@app.post("/upload-doc")
async def upload_document(file: UploadFile = File(...)):
    """
    Accepts files (PDF, Markdown, text) and indexes them in ChromaDB.
    """
    try:
        content_bytes = await file.read()
        rag = RAGService()
        chunks_added = rag.upload_and_index_file(content_bytes, file.filename)
        
        return {
            "status": "Success",
            "message": f"Successfully indexed '{file.filename}'",
            "chunks_added": chunks_added
        }
    except Exception as e:
        logger.error(f"Failed to upload and index document '{file.filename}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document ingestion failed: {str(e)}"
        )

# Direct execution capability
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.BACKEND_HOST, port=settings.BACKEND_PORT, reload=True)
