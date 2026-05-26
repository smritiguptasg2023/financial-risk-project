# GenAI AML Financial Risk Monitor

> A production-grade Anti-Money Laundering pipeline combining **Databricks Medallion Architecture**, **RAG-based policy retrieval**, and a **multi-agent MCP orchestration layer** — built for compliance teams who need explainable, auditable AI decisions.

🔴 **Live Demo:** file:///Users/smritigupta/Documents/genai_project/financial_risk_pipeline/aml-api/aml_mcp_dashboard.html &nbsp;|&nbsp; 👤 **Built by:** Smriti Gupta &nbsp;|&nbsp; 📍 Singapore

---

## Why I Built This

Most AML systems output a risk score with no explanation. Compliance teams and regulators don't just want to know *what* was flagged — they need to know *why*, and auditors need a traceable decision trail that holds up under scrutiny.

This system solves both: every flag is grounded in a retrieved policy document, every decision stage is logged with full AI lineage, and the entire pipeline is protected by role-based access control and prompt injection guards.

---

## Architecture

```
Raw Transactions (Bronze)
        ↓
  Data Cleaning (Silver)
        ↓
  Risk Scoring (Gold)  ←── Apache Spark / Databricks
        ↓
  MCP Orchestrator
   ├── Retriever Agent  ←── FAISS + Sentence Transformers (RAG)
   ├── Reasoner Agent   ←── Policy-based inference
   └── Validator Agent  ←── Rule engine + confidence scoring
        ↓
  FastAPI REST API  ←── aml_full_results.json
        ↓
  Live Risk Dashboard (dashboard.html)
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Data Processing | Apache Spark (Databricks) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector Search | FAISS (IndexFlatL2) |
| Agent Orchestration | Custom MCP (Model Context Protocol) |
| API Framework | FastAPI |
| Logging & Lineage | Python `logging` + custom AI lineage tracker |

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

### Medallion Architecture

| Layer | Purpose |
|-------|---------|
| **Bronze** | Raw transaction ingestion via Spark DataFrame |
| **Silver** | Deduplication and null filtering |
| **Gold** | Risk scoring with business rules (amount + country-based) |

### Risk Scoring Logic

| Condition | Score Added |
|-----------|-------------|
| Amount > 20,000 | +3 |
| Amount > 10,000 | +2 |
| All other amounts | +1 |
| Country on sanctions list | +3 |
| **Final band: High** | Score ≥ 2 |
| **Final band: Low** | Score < 2 |

### MCP Multi-Agent Pipeline

**MCPRetrieverAgent**
Queries a FAISS vector index of AML policy documents using `sentence-transformers/all-MiniLM-L6-v2`. Returns the top-k most relevant policy excerpts for the transaction query.

**MCPReasonerAgent**
Builds structured reasoning output: decision basis, risk factors, policy references, and a plain-language summary. Only invoked for high-risk transactions.

**MCPValidatorAgent**
Applies rule-based checks — high value threshold, sanctioned country, policy match — and outputs flags with a confidence level (High / Medium / Low).

**AgentRouter**
Dynamically routes each transaction. Low-risk transactions use the Retriever only. High-risk transactions invoke the full Retriever → Reasoner → Validator chain.

---

## Security & Governance

| Feature | Description |
|---------|-------------|
| **Prompt Injection Guard** | Blocks known adversarial query patterns before any agent is invoked |
| **Unsafe Query Filter** | Rejects queries containing sensitive keywords (PII, passwords, API keys) |
| **Data Masking** | Customer IDs are partially masked before processing |
| **RBAC** | Three roles: `analyst`, `compliance_officer`, `admin` — each with scoped permissions |
| **Audit Logging** | Every analysis logged with role, action, risk score, and flags |
| **AI Lineage Tracking** | Full step-by-step lineage across retrieval, reasoning, validation, and final decision |
| **LLMOps Metrics** | Per-transaction timing captured for retrieval, reasoning, and validation stages |

### RBAC Reference

| Role | Permissions |
|------|-------------|
| `analyst` | `view_risk` |
| `compliance_officer` | `view_risk`, `view_reasoning` |
| `admin` | All permissions |

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
| `GET` | `/lineage/{txn_id}` | Full AI lineage trace for a transaction |
| `GET` | `/reasoning/{txn_id}` | Reasoning output for a transaction |
| `GET` | `/summary` | Aggregate counts + average retrieval time |
| `GET` | `/dashboard` | Serves `dashboard.html` |

---

## Setup & Installation

### Prerequisites

- Python 3.9+
- Databricks Runtime (for `financial_risk_pipeline.py`)

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

API will be available at `http://localhost:8000`  
Dashboard will be available at `http://localhost:8000/dashboard`

### Run the Pipeline (Databricks)

1. Upload `financial_risk_pipeline.py` as a Databricks notebook
2. Attach to a cluster with the required libraries installed
3. Run all cells top to bottom
4. Export `aml_full_results.json` using the download button rendered in the final cell
5. Place `aml_full_results.json` in the same directory as `main.py` before starting the API server

---

## Sample Transactions

The pipeline includes five sample transactions covering a range of risk profiles:

| TXN ID | Amount (USD) | Country | Risk Band | Flags |
|--------|-------------|---------|-----------|-------|
| TXN001 | 15,000 | Singapore | High | High Value |
| TXN002 | 500 | Singapore | Low | None |
| TXN003 | 25,000 | Country A (Sanctioned) | High | High Value, Sanctioned, Policy Triggered |
| TXN004 | 8,000 | India | Low | None |
| TXN005 | 12,000 | Country B (Sanctioned) | High | High Value, Sanctioned, Policy Triggered |

> **Note:** Sanctioned country names are anonymised in this demo. In production, this list is configurable via your compliance team's jurisdiction policy.

---

## Output Schema

Each entry in `aml_full_results.json` follows this structure:

```json
{
  "status": "SUCCESS",
  "txn": {
    "txn_id": "TXN001",
    "customer_id": "C001****",
    "amount": 15000,
    "country": "Singapore"
  },
  "route": ["retriever", "reasoner", "validator"],
  "docs": ["Transactions above 10000 must be flagged", "..."],
  "reasoning": {
    "decision_basis": [],
    "risk_factors": ["High Value Transaction"],
    "policy_references": [],
    "summary": "Transaction exceeds AML threshold"
  },
  "validation": {
    "flags": ["High Value"],
    "confidence": "High",
    "rule_hits": {
      "high_value": true,
      "sanctioned_country": false,
      "policy_triggered": false
    }
  },
  "flags": ["High Value"],
  "confidence": "High",
  "risk_score": 2,
  "risk_band": "High",
  "metrics": {
    "retrieval_time": 0.012,
    "reasoning_time": 0.003,
    "total_flags": 1
  },
  "ai_lineage": [
    {
      "stage": "retrieval",
      "timestamp": 1234567890.0,
      "input": "...",
      "output": "..."
    }
  ]
}
```

---

## Key Design Decisions

**Why MCP multi-agent over a single model call?**  
Each agent has a single responsibility — retrieval, reasoning, and validation are cleanly separated. This makes each stage independently testable, debuggable, and replaceable without touching the rest of the pipeline.

**Why RAG over fine-tuning?**  
AML policies change frequently. RAG allows the knowledge base to be updated without retraining. Adding a new policy document is a single vector store operation.

**Why FastAPI over a notebook output?**  
The REST API decouples the Databricks pipeline from the compliance dashboard. The same API can serve web dashboards, SIEM integrations, or downstream alerting systems.

---

## Roadmap

- [ ] Streaming results via WebSocket for real-time transaction monitoring
- [ ] Configurable sanctions list via environment variables
- [ ] Authentication layer (JWT) on FastAPI endpoints
- [ ] PostgreSQL backend to replace JSON file storage
- [ ] Grafana dashboard integration for LLMOps metrics

---

## License

MIT License — free to use, modify, and distribute with attribution.

---

## Author

**Smriti Gupta**  
Data Engineer | Databricks · GenAI · RAG · LLMOps  
📍 Singapore | Open to opportunities locally and remote worldwide  
🔗 [LinkedIn](https://linkedin.com/in/yourprofile) · [GitHub](https://github.com/yourusername)