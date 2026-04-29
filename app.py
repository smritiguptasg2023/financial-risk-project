import time
import logging
import numpy as np
import pandas as pd

from fastapi import FastAPI
from sentence_transformers import SentenceTransformer
import faiss

# -------------------------------
# LLMOPS LOGGING SETUP
# -------------------------------
logging.basicConfig(
    filename="app.log",
    filemode="a",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.info("GenAI Risk System Started")

# -------------------------------
# FASTAPI APP
# -------------------------------
app = FastAPI()

# =========================================================
# SECURITY & GOVERNANCE LAYER
# =========================================================

def prompt_injection_guard(query: str):
    suspicious_patterns = [
        "ignore previous",
        "disregard instructions",
        "reveal system prompt",
        "show hidden",
        "bypass rules",
        "system prompt"
    ]

    for pattern in suspicious_patterns:
        if pattern in query.lower():
            return {"allowed": False, "reason": "Prompt injection attempt detected"}

    return {"allowed": True}


def mask_sensitive_data(txn):
    txn = txn.copy()
    if "customer_id" in txn:
        txn["customer_id"] = "CXXX-****"
    return txn


ROLE_PERMISSIONS = {
    "analyst": ["view_risk"],
    "compliance_officer": ["view_risk", "view_reasoning"],
    "admin": ["view_all"]
}


def check_access(role, action):
    allowed = ROLE_PERMISSIONS.get(role, [])
    return action in allowed or "view_all" in allowed


def audit_log(event):
    log_entry = {
        "txn_id": event["txn_id"],
        "role": event.get("role"),
        "action": event.get("action"),
        "timestamp": time.time(),
        "risk_score": event.get("risk_score"),
        "flags": event.get("flags")
    }

    logging.info(f"AUDIT_LOG: {log_entry}")
    return log_entry


# -------------------------------
# GOLD LAYER (DATABRICKS OUTPUT SIMULATION)
# -------------------------------
gold_df = pd.DataFrame([
    {
        "transaction_id": "TXN001",
        "amount": 15000,
        "country": "North Korea",
        "risk_score": 6,
        "risk_category": "High"
    },
    {
        "transaction_id": "TXN002",
        "amount": 5000,
        "country": "Singapore",
        "risk_score": 1,
        "risk_category": "Low"
    }
])

# -------------------------------
# RAG POLICY BASE
# -------------------------------
policy_docs = [
    "Transactions above 10000 USD must be flagged for AML review",
    "Countries under sanctions require enhanced due diligence",
    "Repeated high-value transfers may indicate structuring",
    "Crypto or offshore transfers require additional compliance checks"
]

# -------------------------------
# EMBEDDINGS + FAISS
# -------------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")

doc_embeddings = np.array(model.encode(policy_docs)).astype("float32")

index = faiss.IndexFlatL2(doc_embeddings.shape[1])
index.add(doc_embeddings)


def retrieve(query, top_k=2):
    query_emb = np.array(model.encode([query])).astype("float32")
    _, indices = index.search(query_emb, top_k)
    return [policy_docs[i] for i in indices[0]]


# -------------------------------
# AGENTS
# -------------------------------
def retriever_agent(query):
    return retrieve(query)


def reasoning_agent(txn, context):
    return (
        f"Transaction {txn['transaction_id']} is evaluated. "
        f"Amount {txn['amount']} in {txn['country']}. "
        f"Policies: {context}. "
        f"Conclusion: AML evaluation completed."
    )


def validation_agent(txn, context):
    flags = []

    if txn["amount"] > 10000:
        flags.append("High Value Transaction")

    if txn["country"] in ["North Korea", "Iran", "Nigeria"]:
        flags.append("High Risk Jurisdiction")

    if "sanctions" in " ".join(context).lower():
        flags.append("Sanctions Triggered")

    return flags


# -------------------------------
# ROUTER (UNCHANGED)
# -------------------------------
class AgentRouter:
    def route(self, txn):
        route = ["retriever"]

        if txn["amount"] > 10000:
            route += ["reasoner", "validator"]

        if txn["risk_category"] == "Low":
            route = ["retriever", "reasoner"]

        return list(set(route))


# -------------------------------
# LLMOPS TRACKER (RESTORED)
# -------------------------------
class LLMOpsTracker:
    def record(self, txn_id, stage_times, flags):
        metrics = {
            "txn_id": txn_id,
            "retrieval_time": stage_times.get("retrieval", 0),
            "reasoning_time": stage_times.get("reasoning", 0),
            "validation_time": stage_times.get("validation", 0),
            "total_flags": len(flags),
            "timestamp": time.time()
        }

        logging.info(f"LLMOps Metrics: {metrics}")
        return metrics


# -------------------------------
# ORCHESTRATOR
# -------------------------------
class RiskOrchestrator:

    def __init__(self):
        self.router = AgentRouter()
        self.llmops = LLMOpsTracker()

    def run(self, txn, query, role):

        # SECURITY CHECK
        sec = prompt_injection_guard(query)
        if not sec["allowed"]:
            return {"error": sec["reason"]}

        txn = mask_sensitive_data(txn)

        route = self.router.route(txn)

        stage_times = {}
        flags = []
        reasoning = None

        # -----------------------
        # RETRIEVAL
        # -----------------------
        start = time.time()
        context = retriever_agent(query)
        stage_times["retrieval"] = round(time.time() - start, 3)

        # -----------------------
        # REASONING
        # -----------------------
        start = time.time()
        reasoning = reasoning_agent(txn, context)
        stage_times["reasoning"] = round(time.time() - start, 3)

        # -----------------------
        # VALIDATION
        # -----------------------
        start = time.time()
        flags = validation_agent(txn, context)
        stage_times["validation"] = round(time.time() - start, 3)

        # -----------------------
        # LLMOPS
        # -----------------------
        metrics = self.llmops.record(
            txn["transaction_id"],
            stage_times,
            flags
        )

        # -----------------------
        # FINAL RESPONSE (FIXED + COMPLETE)
        # -----------------------
        return {
            "transaction_id": txn["transaction_id"],
            "amount": txn["amount"],
            "country": txn["country"],

            # FIXED FIELDS (NOW ALWAYS PRESENT)
            "risk_score": txn["risk_score"],
            "risk_category": txn["risk_category"],

            "route_used": route,
            "context": context,
            "reasoning": reasoning,
            "validation_flags": flags,
            "llmops_metrics": metrics
        }


orchestrator = RiskOrchestrator()

# -------------------------------
# API ENDPOINT
# -------------------------------
@app.get("/")
def home():
    return {"status": "GenAI AML System Running"}


@app.get("/analyze/{transaction_id}")
def analyze(transaction_id: str, role: str = "analyst", query: str = None):

    txn_row = gold_df[gold_df["transaction_id"] == transaction_id]

    if txn_row.empty:
        return {"error": "Transaction not found"}

    # CRITICAL FIX: convert to dict
    txn = txn_row.iloc[0].to_dict()

    if query is None:
        query = f"Analyze AML risk: Amount {txn['amount']} Country {txn['country']}"

    result = orchestrator.run(txn, query, role)

    audit_log({
        "txn_id": transaction_id,
        "role": role,
        "action": "AML_ANALYSIS",
        "risk_score": txn["risk_score"],
        "flags": result.get("validation_flags")
    })

    return result