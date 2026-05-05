# NTT DATA — AML Financial Risk Monitor (FRM)

A GenAI-powered Anti-Money Laundering (AML) pipeline built on **Databricks**, combining a multi-agent MCP (Model Context Protocol) architecture, RAG-based policy retrieval, and a FastAPI backend for real-time risk analysis and monitoring.

---

## Overview

This system processes financial transactions through a medallion data architecture (Bronze → Silver → Gold), evaluates AML risk using chained AI agents, and exposes results via a REST API. It is designed for compliance teams to detect high-risk transactions, enforce policy, and maintain full AI decision lineage.

---

## Architecture

```
Raw Transactions (Bronze)
        ↓
  Data Cleaning (Silver)
        ↓
  Risk Scoring (Gold)  ←── Spark / Databricks
        ↓
  MCP Orchestrator
   ├── Retriever Agent  ←── FAISS + Sentence Transformers (RAG)
   ├── Reasoner Agent   ←── Policy-based inference
   └── Validator Agent  ←── Rule engine + confidence scoring
        ↓
  FastAPI REST API  ←── aml_full_results.json
        ↓
  Dashboard (dashboard.html)
```

---

## Repository Structure

```
.
├── financial_risk_pipeline.py   # Databricks notebook: full AML pipeline
├── main.py                      # FastAPI REST API server
├── aml_full_results.json        # Pre-processed transaction results
├── dashboard.html               # Frontend dashboard (served by API)
└── README.md
```

---

## Pipeline: `financial_risk_pipeline.py`

### Medallion Layers

| Layer | Purpose |
|-------|---------|
| **Bronze** | Raw transaction ingestion via Spark DataFrame |
| **Silver** | Deduplication and null filtering |
| **Gold** | Risk scoring with business rules (amount + country-based) |

### Risk Scoring Logic

- Amount > 20,000 → score +3
- Amount > 10,000 → score +2
- Otherwise → score +1
- Country in `["North Korea", "Nigeria"]` → score +3
- Final band: `High` if score ≥ 2, else `Low`

### MCP Agent Pipeline

**MCPRetrieverAgent** — Queries a FAISS vector index of AML policy documents using `sentence-transformers/all-MiniLM-L6-v2`.

**MCPReasonerAgent** — Builds a structured reasoning output: decision basis, risk factors, policy references, and a plain-language summary.

**MCPValidatorAgent** — Applies rule-based checks (high value, sanctioned country, policy match) and outputs flags + confidence level.

**AgentRouter** — Dynamically routes each transaction: low-risk transactions only use the Retriever, while high-risk ones invoke all three agents.

### Security & Governance

- **Prompt Injection Guard** — Blocks known adversarial query patterns.
- **Unsafe Query Filter** — Blocks queries containing sensitive keywords (PII, passwords, API keys).
- **Data Masking** — Customer IDs are partially masked before processing.
- **RBAC** — Role-based access control with three roles: `analyst`, `compliance_officer`, `admin`.
- **Audit Logging** — Every transaction analysis is logged with role, action, risk score, and flags.
- **AI Lineage Tracking** — Full step-by-step lineage recorded across retrieval, reasoning, validation, and final decision stages.
- **LLMOps Metrics** — Per-transaction timing captured for retrieval, reasoning, and validation stages.

---

## API Server: `main.py`

Built with **FastAPI**. Loads `aml_full_results.json` at startup and serves all endpoints in-memory.

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check + transaction count |
| `GET` | `/transactions` | All transaction results |
| `GET` | `/transaction/{txn_id}` | Single transaction by ID |
| `GET` | `/flags` | All High-risk transactions |
| `GET` | `/metrics` | LLMOps metrics for all transactions |
| `GET` | `/lineage/{txn_id}` | AI lineage trace for a transaction |
| `GET` | `/reasoning/{txn_id}` | Reasoning output for a transaction |
| `GET` | `/summary` | Aggregate counts + avg retrieval time |
| `GET` | `/dashboard` | Serves `dashboard.html` |

---

## Setup & Installation

### Prerequisites

- Python 3.9+
- Databricks Runtime (for `financial_risk_pipeline.py`)
- Node.js (optional, for dashboard development)

### Install Dependencies

```bash
pip install fastapi uvicorn sentence-transformers faiss-cpu pyspark
```

For the Databricks notebook, install within the cluster:

```python
%pip install sentence-transformers faiss-cpu
```

### Run the API Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

### Run the Pipeline (Databricks)

1. Upload `financial_risk_pipeline.py` as a Databricks notebook.
2. Attach to a cluster with the required libraries installed.
3. Run all cells top to bottom.
4. Export `aml_full_results.json` using the download button rendered in the final cell.

---

## Sample Transactions

The pipeline includes five sample transactions covering a range of risk profiles:

| TXN ID | Amount | Country | Expected Risk |
|--------|--------|---------|---------------|
| TXN001 | 15,000 | Singapore | High |
| TXN002 | 500 | Singapore | Low |
| TXN003 | 25,000 | Nigeria | High |
| TXN004 | 8,000 | India | Low |
| TXN005 | 12,000 | North Korea | High |

---

## Output Schema

Each entry in `aml_full_results.json` contains:

```json
{
  "status": "SUCCESS",
  "txn": { "txn_id": "...", "customer_id": "C001****", "amount": 15000, "country": "..." },
  "route": ["retriever", "reasoner", "validator"],
  "docs": ["...policy snippets..."],
  "reasoning": { "decision_basis": [], "risk_factors": [], "summary": "..." },
  "validation": { "flags": [], "confidence": "High", "rule_hits": {} },
  "flags": ["High Value", "Sanctioned"],
  "confidence": "High",
  "risk_score": 5,
  "risk_band": "High",
  "metrics": { "retrieval_time": 0.012, "reasoning_time": 0.003, "total_flags": 2 },
  "ai_lineage": [{ "stage": "retrieval", "timestamp": 0, "input": "...", "output": "..." }]
}
```

---

## RBAC Reference

| Role | Permissions |
|------|-------------|
| `analyst` | `view_risk` |
| `compliance_officer` | `view_risk`, `view_reasoning` |
| `admin` | All permissions |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Data Processing | Apache Spark (Databricks) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector Search | FAISS (IndexFlatL2) |
| Agent Orchestration | Custom MCP (Model Context Protocol) |
| API Framework | FastAPI |
| Logging | Python `logging` module |

---

## License

Proprietary — NTT DATA. All rights reserved.
