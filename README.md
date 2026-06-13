# AI DevOps SRE Copilot

An intelligent, AI-powered Site Reliability Engineering (SRE) assistant that operates through **Discord** (extensible to Slack) to help developers diagnose infrastructure issues, analyze logs, inspect system metrics, search troubleshooting runbooks, and provide automated root cause analysis.

Built using **FastAPI**, **Google Gemini 2.5 Flash**, **LangGraph**, **ChromaDB**, and **discord.py**.

---

## Architecture Overview

This Copilot uses a modular, microservice-style design, conforming to clean architecture and dependency injection principles:

```text
copilot-devops/
├── backend-api/             # FastAPI App containing the SRE Agent Workflow & RAG
│   ├── app/
│   │   ├── api/             # API routes
│   │   ├── core/            # Configuration & Settings
│   │   ├── models/          # Pydantic schemas (Request/Response validation)
│   │   ├── services/        # Service integrations (Kubernetes mock, Prometheus mock, RAG)
│   │   └── agents/          # LangGraph SRE Multi-Agent workflow
│   └── tests/               # pytest test cases
├── discord-bot/             # discord.py bot implementing modern slash commands
├── monitoring/              # Prometheus and Grafana configurations
├── docs/                    # Architectural documents and troubleshooting runbooks
├── .github/workflows/       # GitHub Actions CI/CD configuration
├── docker-compose.yml       # Dev orchestration
└── .env                     # Local credentials and variables
```

### Multi-Agent SRE Workflow (LangGraph)

The core diagnosis pipeline is built as a stateful graph using **LangGraph**:

```mermaid
graph TD
    User([User Trigger: /diagnose service]) --> Coord[Coordinator Node]
    Coord --> |Fetch Logs & Metrics| InitState[Initialize State]
    InitState --> LogAgent[Log Analysis Agent]
    LogAgent --> MetricAgent[Metrics Analysis Agent]
    MetricAgent --> DocAgent[Documentation RAG Agent]
    DocAgent --> RootCauseAgent[Root Cause Agent]
    RootCauseAgent --> RecAgent[Recommendation Agent]
    RecAgent --> Coord
    Coord --> FinalEmbed([Discord Response Embed])

    style Coord fill:#1f77b4,stroke:#333,stroke-width:2px,color:#fff
    style LogAgent fill:#ff7f0e,stroke:#333,stroke-width:1px,color:#fff
    style MetricAgent fill:#2ca02c,stroke:#333,stroke-width:1px,color:#fff
    style DocAgent fill:#d62728,stroke:#333,stroke-width:1px,color:#fff
    style RootCauseAgent fill:#9467bd,stroke:#333,stroke-width:2px,color:#fff
    style RecAgent fill:#8c564b,stroke:#333,stroke-width:1px,color:#fff
```

1. **Log Analysis Agent**: Parses stdout, detects exceptions/crashes, and extracts warning context.
2. **Metrics Analysis Agent**: Inspects CPU, Memory limits, HTTP Request latency, and failures.
3. **Documentation Agent**: Queries ChromaDB for matching troubleshooting runbooks.
4. **Root Cause Agent**: Synthesizes inputs to deduce the primary issue and calculates a confidence score.
5. **Recommendation Agent**: Suggests exact shell commands and fixes.

---

## Technology Stack

* **Backend**: Python 3.12, FastAPI, Uvicorn
* **AI Pipeline**: Google Gemini 2.5 Flash, LangGraph, LangChain
* **Vector Store**: ChromaDB with `SentenceTransformers` (all-MiniLM-L6-v2) for offline embeddings
* **Database**: PostgreSQL (Dockerized)
* **Monitoring**: Prometheus (metrics scraping), Grafana (visualization)
* **Interface**: Discord Bot (built with `discord.py`)
* **DevOps**: Docker, Docker Compose, GitHub Actions

---

## Getting Started

### 1. Prerequisites
* Python 3.12 (if running locally without Docker)
* Docker & Docker Compose
* Google Gemini API Key
* Discord Bot Token (with Applications.Commands gateway intent enabled)

### 2. Configure Credentials
Copy `.env.example` to `.env` and fill in the values:
```bash
cp .env.example .env
```
Ensure you set your `DISCORD_TOKEN` and `GEMINI_API_KEY`. (Note: If `GEMINI_API_KEY` is not provided, the backend falls back to high-fidelity SRE rules engines to support offline development and test runs.)

### 3. Run with Docker Compose (Recommended)
This starts all components (FastAPI backend, Discord bot, Postgres Database, Prometheus, and Grafana) simultaneously:

```bash
docker-compose up --build -d
```

Verify everything is running:
* **FastAPI Docs**: http://localhost:8000/docs
* **Prometheus**: http://localhost:9090
* **Grafana**: http://localhost:3000 (User: `admin`, Pass: `admin`)
* **Discord Bot**: Logged in and listing commands in your server!

---

## Discord Slash Commands Guide

The bot registers and supports the following slash commands:

* **/help** - Returns a structured embed guide of SRE capabilities.
* **/status** - Checks connectivity to FastAPI Backend, ChromaDB, and Gemini API keys.
* **/logs `[service]`** - Outputs the last 100 lines of container logs for a service.
  * *Example*: `/logs payment-service`
* **/diagnose `[service]`** - Runs the multi-agent incident response pipeline.
  * *Example*: `/diagnose payment-service`
  * *Output*: A comprehensive color-coded embed detailing pod status, log errors, metric graphs anomalies, root cause diagnosis, and copy-paste remediation commands.
* **/explain-error `[error_text]`** - Explains stack traces or error logs with suggested solutions.
* **/search-docs `[query]`** - Finds matching documentation chunks in the ChromaDB vector database.
* **/ask `[question]`** - Generates SRE answers utilizing indexed runbook context.

---

## FastAPI REST Endpoints

If you wish to query the API programmatically:

* `POST /diagnose` - Triggers the SRE workflow.
  * Payload: `{"service_name": "payment-service"}`
* `POST /explain-error` - Analyzes logs.
  * Payload: `{"error_message": "string"}`
* `POST /search-docs` - Similarity search in runbooks.
  * Payload: `{"query": "database timeout", "limit": 3}`
* `POST /ask` - RAG Question answering.
  * Payload: `{"question": "How to scale pod memory?"}`
* `POST /upload-doc` - Ingests new PDF, Markdown, or text documentation.
  * Payload: Multipart form file upload.
* `GET /health` - Liveness health checks.

---

## Running Verification Tests

Run automated tests using pytest:

### Local Python Environment:
```bash
cd backend-api
pip install -r requirements.txt
pytest
```

### Running inside Docker:
```bash
docker exec -it copilot-backend pytest
```

---

## Mock Incident Scenarios (Out-of-the-Box Demos)
You can test the SRE reasoning immediately with these simulated microservices:
1. **`payment-service`**: Simulates a database connection timeout leading to a `CrashLoopBackOff` state.
2. **`analytics-service`**: Simulates a resource memory leak spike leading to container `OOMKilled` (Exit code 137).
3. **`frontend-service`**: Simulates downstream gateway timeouts (504 errors) waiting on the payment service.
4. **`auth-service`**: Simulates normal operation with minor rate limit warnings.
