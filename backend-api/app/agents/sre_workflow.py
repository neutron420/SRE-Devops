import os
import logging
from typing import Dict, Any, List, TypedDict
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END

from app.services.k8s_service import K8sService
from app.services.prometheus_service import PrometheusService
from app.services.rag_service import RAGService
from app.core.config import settings

logger = logging.getLogger(__name__)

# Define the shared agent state
class SREState(TypedDict):
    service_name: str
    raw_logs: str
    raw_metrics: Dict[str, Any]
    runbook_context: str
    log_analysis: str
    metrics_analysis: str
    root_cause_analysis: str
    recommendations: str
    confidence_score: float
    final_report: Dict[str, Any]

# Helper to initialize Gemini LLM
def get_llm():
    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key == "your_gemini_api_key_here":
        logger.warning("GEMINI_API_KEY is not set. Agents will use local fallback heuristic analysis.")
        return None
    try:
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.1
        )
    except Exception as e:
        logger.error(f"Error initializing Google Gemini LLM: {str(e)}")
        return None

# ==================== AGENT NODES ====================

def log_analysis_node(state: SREState) -> Dict[str, Any]:
    """
    Agent 1: Parses logs, detects common issues, extracts errors.
    """
    logger.info("Running Log Analysis Agent...")
    logs = state.get("raw_logs", "")
    service = state.get("service_name", "")
    llm = get_llm()

    if not logs:
        return {"log_analysis": "No logs provided for analysis."}

    if llm:
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are a Senior Log Analysis Agent. Your task is to parse application logs for the service '{service}', "
                    "identify errors, stack traces, warnings, or anomalies, and summarize your findings in a structured format."
                )),
                ("user", "Analyze the following logs and return the key issue found:\n\n{logs}")
            ])
            chain = prompt | llm
            response = chain.invoke({"service": service, "logs": logs})
            return {"log_analysis": response.content}
        except Exception as e:
            logger.error(f"Log analysis LLM execution failed: {str(e)}")
            # Fall back to heuristic

    # Heuristic fallback (Mock Analysis)
    if "Connection timeout" in logs or "Failed to connect to database" in logs:
        analysis = (
            "Detected database connectivity timeout error. The service fails during connection pool initialization "
            "when trying to contact postgres-db.default.svc.cluster.local:5432 after 30 seconds."
        )
    elif "OutOfMemory" in logs or "Heap memory usage exceeding" in logs:
        analysis = (
            "Detected OutOfMemory (OOM) error. The service's heap space was exhausted while processing a large batch "
            "of events (up to 250,000 items), causing a fatal failure."
        )
    elif "Gateway Timeout" in logs:
        analysis = (
            "Detected 504 Gateway Timeout error downstream. The service is experiencing slow responses when querying "
            "the payment-service."
        )
    else:
        analysis = f"Log analysis complete. Identified general operational logs. Clean run or unknown warning present."

    return {"log_analysis": analysis}


def metrics_analysis_node(state: SREState) -> Dict[str, Any]:
    """
    Agent 2: Analyzes CPU, Memory, Latency, and Availability.
    """
    logger.info("Running Metrics Analysis Agent...")
    metrics = state.get("raw_metrics", {})
    service = state.get("service_name", "")
    llm = get_llm()

    if not metrics:
        return {"metrics_analysis": "No metrics available for analysis."}

    if llm:
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are a Senior SRE Metrics Analysis Agent. Analyze the provided CPU, memory, request latency, "
                    "and error rate metrics for '{service}' and identify resource saturation, performance bottlenecking, "
                    "or service degradation."
                )),
                ("user", "Metrics data:\n{metrics}")
            ])
            chain = prompt | llm
            response = chain.invoke({"service": service, "metrics": str(metrics)})
            return {"metrics_analysis": response.content}
        except Exception as e:
            logger.error(f"Metrics analysis LLM execution failed: {str(e)}")

    # Heuristic fallback
    analysis = []
    # Simple check on CPU / Memory / Latency from raw values
    cpu_vals = [pt["value"] for pt in metrics.get("cpu", {}).get("values", []) if pt["value"] > 0]
    mem_vals = [pt["value"] for pt in metrics.get("memory", {}).get("values", []) if pt["value"] > 0]
    latency_vals = [pt["value"] for pt in metrics.get("latency", {}).get("values", []) if pt["value"] > 0]
    error_vals = [pt["value"] for pt in metrics.get("error_rate", {}).get("values", []) if pt["value"] > 0]

    if error_vals and max(error_vals) >= 100.0:
        analysis.append("Critical: Error rate hit 100%. The service was completely unavailable.")
    if latency_vals and max(latency_vals) >= 5000.0:
        analysis.append(f"Performance Degradation: Request latency spiked up to {max(latency_vals)}ms.")
    
    # Check limit comparison
    mem_limit = metrics.get("memory", {}).get("limit_mib", 512)
    if mem_vals and max(mem_vals) >= (mem_limit * 0.9):
        analysis.append(f"Memory Saturation: Memory usage hit {max(mem_vals)}MiB (Limit: {mem_limit}MiB), indicating an OOM event or memory leak.")

    if not analysis:
        analysis.append("All resource utilization (CPU, memory, latency) falls within safe operational baseline boundaries.")

    return {"metrics_analysis": "\n".join(analysis)}


def documentation_node(state: SREState) -> Dict[str, Any]:
    """
    Agent 3: Searches the vector database for relevant runbooks & documentation.
    """
    logger.info("Running Documentation Agent...")
    service = state.get("service_name", "")
    log_analysis = state.get("log_analysis", "")
    
    # Formulate search query
    query = f"{service} "
    if "database" in log_analysis.lower() or "timeout" in log_analysis.lower():
        query += "database timeout connection fail"
    elif "oom" in log_analysis.lower() or "memory" in log_analysis.lower() or "limit" in log_analysis.lower():
        query += "oomkilled memory heap leak limit"
    else:
        query += "troubleshooting guide runbook"

    try:
        rag = RAGService()
        results = rag.search_documents(query, limit=2)
        
        context_blocks = []
        for res in results:
            context_blocks.append(
                f"Source: {res['metadata'].get('filename', 'Unknown')}\n"
                f"Content:\n{res['content']}"
            )
        
        context = "\n\n---\n\n".join(context_blocks) if context_blocks else "No relevant runbooks or documentation found in vector store."
        return {"runbook_context": context}
    except Exception as e:
        logger.error(f"Documentation lookup failed: {str(e)}")
        return {"runbook_context": "Error accessing internal documentation vector database."}


def root_cause_node(state: SREState) -> Dict[str, Any]:
    """
    Agent 4: Combines log/metrics analyses & runbook context to identify root cause and calculate confidence.
    """
    logger.info("Running Root Cause Agent...")
    log_an = state.get("log_analysis", "")
    metric_an = state.get("metrics_analysis", "")
    doc_an = state.get("runbook_context", "")
    service = state.get("service_name", "")
    llm = get_llm()

    if llm:
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are a Principal Root Cause Analysis (RCA) SRE Agent. Your job is to analyze log and metrics summaries, "
                    "correlate them with internal runbooks, and output: "
                    "1. A clear, definitive Root Cause Diagnosis.\n"
                    "2. A Confidence Score between 0.0 (uncertain) and 1.0 (fully certain), formatted exactly as: 'CONFIDENCE: <score>'.\n"
                    "Be structured, factual, and direct."
                )),
                ("user", (
                    f"Service: {service}\n"
                    f"Log Analysis Summary: {log_an}\n"
                    f"Metrics Analysis Summary: {metric_an}\n"
                    f"Relevant Runbooks: {doc_an}"
                ))
            ])
            chain = prompt | llm
            response = chain.invoke({})
            
            # Parse confidence score
            content = response.content
            confidence = 0.8  # default
            for line in content.split("\n"):
                if "CONFIDENCE:" in line.upper():
                    try:
                        confidence = float(line.upper().replace("CONFIDENCE:", "").strip())
                    except ValueError:
                        pass
            
            return {
                "root_cause_analysis": content,
                "confidence_score": confidence
            }
        except Exception as e:
            logger.error(f"Root Cause LLM execution failed: {str(e)}")

    # Heuristic fallback
    if "database" in log_an.lower():
        rc = (
            "**Root Cause**: The application failed to establish a database connection because the connection pool "
            "initialization timed out (30 seconds limit) reaching 'postgres-db.default.svc.cluster.local'. This points to "
            "either a service name DNS resolution error or a security network policy blocking traffic on port 5432."
        )
        conf = 0.95
    elif "memory" in log_an.lower() or "oom" in log_an.lower():
        rc = (
            "**Root Cause**: The container was terminated by the Kubernetes node kernel (OOMKilled) because its memory consumption "
            "climbed linearly to 512MiB, exhausting its resource limit. This is a classic memory leak/heap exhaustion occurring "
            "during large user event batch operations."
        )
        conf = 0.90
    else:
        rc = (
            "**Root Cause**: General system warning. Operational components are healthy, but minor transient connection resets "
            "or client errors were logged. No active outage detected."
        )
        conf = 0.50

    return {"root_cause_analysis": rc, "confidence_score": conf}


def recommendation_node(state: SREState) -> Dict[str, Any]:
    """
    Agent 5: Suggests remediation steps, diagnostic commands, and next actions.
    """
    logger.info("Running Recommendation Agent...")
    rc_analysis = state.get("root_cause_analysis", "")
    doc_an = state.get("runbook_context", "")
    service = state.get("service_name", "")
    llm = get_llm()

    if llm:
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are an SRE Recommendation Agent. Suggest immediate fixes, troubleshooting steps, and "
                    "Kubernetes or command-line commands to resolve the problem. Provide clear formatting."
                )),
                ("user", (
                    f"Service: {service}\n"
                    f"Root Cause Analysis: {rc_analysis}\n"
                    f"Runbook Suggestions: {doc_an}"
                ))
            ])
            chain = prompt | llm
            response = chain.invoke({})
            return {"recommendations": response.content}
        except Exception as e:
            logger.error(f"Recommendation LLM execution failed: {str(e)}")

    # Heuristic fallback
    if "database" in rc_analysis.lower():
        recs = (
            "### Immediate Remediation Steps:\n"
            "1. **Test DNS Connectivity**: Verify if the pod can resolve the database hostname:\n"
            "   ```bash\n"
            "   kubectl exec -it deployment/payment-service -- nslookup postgres-db\n"
            "   ```\n"
            "2. **Verify TCP Socket**: Try contacting the DB directly on port 5432:\n"
            "   ```bash\n"
            "   kubectl exec -it deployment/payment-service -- nc -zvw3 postgres-db 5432\n"
            "   ```\n"
            "3. **Check Network Policies**: Ensure that the database namespace allows incoming traffic from the backend namespace.\n"
            "4. **Update DB Endpoint Config**: Verify host settings in the Helm values or ConfigMap configs."
        )
    elif "memory" in rc_analysis.lower() or "oom" in rc_analysis.lower():
        recs = (
            "### Immediate Remediation Steps:\n"
            "1. **Scale memory limit**: Bump the container memory limit in the deployment spec to prevent kernel kills:\n"
            "   ```bash\n"
            "   kubectl set resources deployment/analytics-service --limits=memory=1Gi --requests=memory=512Mi\n"
            "   ```\n"
            "2. **Force roll pod**: Trigger a rolling restart to release leaked resources temporarily:\n"
            "   ```bash\n"
            "   kubectl rollout restart deployment/analytics-service\n"
            "   ```\n"
            "3. **Refactor Ingestion**: Update code to process data payloads in streams rather than loading all batch entries in-memory."
        )
    else:
        recs = (
            "### Immediate Remediation Steps:\n"
            "1. Run `kubectl get pods -l app={service}` to check pod availability.\n"
            "2. Enable debug-level application logging to capture intermittent issues."
        )

    return {"recommendations": recs}


# ==================== WORKFLOW ORCHESTRATOR ====================

class SREWorkflow:
    """
    Orchestrates the entire multi-agent LangGraph workflow.
    """

    @property
    def k8s(self):
        return K8sService()

    @property
    def prometheus(self):
        return PrometheusService()

    def __init__(self):
        
        # Build the graph
        workflow = StateGraph(SREState)
        
        # Add nodes
        workflow.add_node("log_analyzer", log_analysis_node)
        workflow.add_node("metrics_analyzer", metrics_analysis_node)
        workflow.add_node("documentation_search", documentation_node)
        workflow.add_node("root_cause_analysis", root_cause_node)
        workflow.add_node("remediation_suggestions", recommendation_node)
        
        # Define sequential edges
        workflow.add_edge("log_analyzer", "metrics_analyzer")
        workflow.add_edge("metrics_analyzer", "documentation_search")
        workflow.add_edge("documentation_search", "root_cause_analysis")
        workflow.add_edge("root_cause_analysis", "remediation_suggestions")
        workflow.add_edge("remediation_suggestions", END)
        
        # Set Entrypoint
        workflow.set_entry_point("log_analyzer")
        
        # Compile
        self.app = workflow.compile()
        logger.info("LangGraph SRE Workflow successfully compiled.")

    def run_diagnosis(self, service_name: str) -> Dict[str, Any]:
        """
        Executes the SRE multi-agent workflow for the given service.
        """
        logger.info(f"Initiating diagnostic run for service: '{service_name}'")
        
        # 1. Fetch raw data from mock systems
        pod_status = self.k8s.get_pod_status(service_name)
        logs = self.k8s.get_pod_logs(service_name)
        metrics = self.prometheus.get_all_metrics(service_name)
        
        # 2. Setup initial state
        initial_state: SREState = {
            "service_name": service_name,
            "raw_logs": logs,
            "raw_metrics": metrics,
            "runbook_context": "",
            "log_analysis": "",
            "metrics_analysis": "",
            "root_cause_analysis": "",
            "recommendations": "",
            "confidence_score": 0.0,
            "final_report": {}
        }
        
        # 3. Execute Graph
        result_state = self.app.invoke(initial_state)
        
        # 4. Formulate the final SRE report structure
        final_report = {
            "service_name": service_name,
            "pod_status": pod_status,
            "log_analysis": result_state["log_analysis"],
            "metrics_analysis": result_state["metrics_analysis"],
            "runbook_matched": result_state["runbook_context"] != "No relevant runbooks or documentation found in vector store.",
            "root_cause": result_state["root_cause_analysis"],
            "recommendations": result_state["recommendations"],
            "confidence_score": result_state["confidence_score"]
        }
        
        return final_report
