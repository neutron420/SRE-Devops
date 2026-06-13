# Architectural Design Document: SRE DevOps Copilot

This document details the architectural decisions, component design, multi-agent SRE workflows, and RAG configuration for the DevOps Copilot.

---

## 1. Design Philosophy

The Copilot is engineered around **Clean Architecture** and **SOLID** principles:
* **Separation of Concerns**: The Discord Bot (presentation layer) is separated from the API Backend (business logic layer). The bot communicates solely via HTTP REST endpoints.
* **Interface Abstractions**: Infrastructure layers (Kubernetes clusters, Prometheus metrics servers) are decoupled via service abstractions (`K8sService`, `PrometheusService`). This allows mock datasets to be swapped with real API clients (`kubernetes-client`, `prometheus-api-client`) without changing the agent workflow logic.
* **Stateful Orchestration**: Rather than using linear agent chains, we use **LangGraph** to model the virtual SRE response team as a stateful, coordinated state machine.

---

## 2. Component Layout & Directory Mapping

```text
               +---------------------------------------+
               |             Discord Guild             |
               +-------------------+-------------------+
                                   |
                         (Slash Commands / Websocket)
                                   v
               +-------------------+-------------------+
               |            Discord Bot                | (discord-bot/)
               +-------------------+-------------------+
                                   |
                             (HTTP REST API)
                                   v
+----------------------------------+------------------------------------+
|                         FastAPI Backend                               | (backend-api/)
|                                                                       |
|  +-----------------------+              +--------------------------+  |
|  |     API Controllers   |              |       Agent System       |  |
|  |  (/diagnose, /ask,    |              |     - Log Analyzer       |  |
|  |   /explain-error,     +------------->|     - Metrics Analyzer   |  |
|  |   /upload-doc)        |              |     - Runbook Lookup     |  |
|  +-----------------------+              |     - Root Cause Engine  |  |
|                                         |     - Recommendation     |  |
|                                         +------------+-------------+  |
|                                                      |                |
+------------------------------------------------------|----------------+
                                                       |
                                        (Abstract Service Clients)
                                                       v
+----------------------+             +-----------------+----------------+
|       ChromaDB       |             | Mock Kubernetes | Mock Prometheus|
|     (Vector DB)      |             |     Cluster     |  Metrics Server|
+----------------------+             +-----------------+----------------+
```

### Key Modules:
1. **API Router (`app/api/`)**: Manages inputs and marshals Pydantic request payloads.
2. **Core Settings (`app/core/`)**: Handles application-wide variables and credentials via env configurations.
3. **Services (`app/services/`)**:
   * `K8sService`: Interacts with cluster resources (extracts logs, pod descriptions, events).
   * `PrometheusService`: Queries Prometheus servers for system indicators (CPU, Memory limits, HTTP Error rates, Latency).
   * `RAGService`: Handles text chunking (`RecursiveCharacterTextSplitter`), local vector embedding generation (`all-MiniLM-L6-v2`), database storage, and similarity search queries.
4. **Agent Workflow (`app/agents/`)**: Defines the LangGraph nodes and SRE state machine.

---

## 3. LangGraph Multi-Agent Team Design

The incident response workflow coordinates specialized nodes that mutate a shared `SREState` dictionary sequentially:

```python
class SREState(TypedDict):
    service_name: str          # Input: service to diagnose
    raw_logs: str              # Input: log output gathered by K8sService
    raw_metrics: dict          # Input: time-series maps from PrometheusService
    runbook_context: str       # Shared: Markdown runbook matched by Documentation Agent
    log_analysis: str          # State: Log anomalies extracted by Log Agent
    metrics_analysis: str      # State: Threshold breaches found by Metric Agent
    root_cause_analysis: str   # State: Correlation details from Root Cause Agent
    recommendations: str       # State: Command suggestions from Recommendation Agent
    confidence_score: float    # State: Probability score from Root Cause Agent
    final_report: dict         # Output: Compiled payload returned to API client
```

### Node Operations:
1. **`log_analyzer`**: Analyzes the raw logs for known error traces.
2. **`metrics_analyzer`**: Analyzes the raw metrics data (CPU, memory, latency, and error rates) to find saturation spikes.
3. **`documentation_search`**: Uses output keyword summaries from log and metrics nodes to query ChromaDB for matching recovery runbooks.
4. **`root_cause_analysis`**: Correlates the log analysis, metrics analysis, and matching runbook. Synthesizes a unified root-cause summary and computes a confidence rating.
5. **`remediation_suggestions`**: Generates CLI remediation commands (e.g. `kubectl scale`, `kubectl set resources`) and next-step actions.

---

## 4. RAG Vector Database (ChromaDB) Setup

We use **ChromaDB** with a persistent local directory (`vector-db/chroma_data`) to prevent data loss on container rebuilds.
* **Embeddings Model**: `sentence-transformers/all-MiniLM-L6-v2`. This model compiles text into 384-dimensional dense vectors. It is highly optimized for technical domain sentences and runs completely local and free without API quota costs.
* **Text Splitting**: Standard LangChain `RecursiveCharacterTextSplitter` configured with a chunk size of 800 characters and a 100-character overlap. This range ensures that code commands and context are not sliced in half during database queries.
* **Database Seeding**: During container boot, the FastAPI startup lifespan scan searches the `docs/runbooks` folder and automatically indexes markdown files (`database_timeout_runbook.md`, `oom_killed_runbook.md`) into the vector collection.
