# Databricks notebook source
# %pip install sentence-transformers faiss-cpu

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import time
import logging
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss
from pyspark.sql.functions import col, when
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

logging.basicConfig(level=logging.INFO)
logging.info("GenAI AML MCP System Started")

# COMMAND ----------

# ============================================
# SECURITY LAYER
# ============================================

suspicious_patterns = [
    "ignore previous instructions",
    "disregard system prompt",
    "reveal system prompt",
    "bypass rules"
]

blocked_keywords = ["confidential", "pii", "password", "api key"]

def prompt_injection_guard(query: str):
    for pattern in suspicious_patterns:
        if pattern in query.lower():
            return {"allowed": False, "reason": "Injection detected"}
    return {"allowed": True}

def unsafe_query_filter(query: str):
    for word in blocked_keywords:
        if word in query.lower():
            return {"allowed": False, "reason": "Unsafe query"}
    return {"allowed": True}

def mask_sensitive_data(txn):
    txn = txn.copy()
    if "customer_id" in txn:
        cid = str(txn["customer_id"])
        txn["customer_id"] = cid[:4] + "****" if len(cid) > 4 else "****"
    return txn

# COMMAND ----------

# ============================================
# ROLE-BASED ACCESS CONTROL (RBAC)
# ============================================

ROLE_PERMISSIONS = {
    "analyst": ["view_risk"],
    "compliance_officer": ["view_risk", "view_reasoning"],
    "admin": ["all"]
}

def check_access(role, action):
    allowed = ROLE_PERMISSIONS.get(role, [])
    return action in allowed or "all" in allowed

# COMMAND ----------

# ============================================
# AUDIT LOGGING + LLMOPS
# ============================================

def audit_log(event):
    log_entry = {
        "txn_id": event.get("txn_id"),
        "role": event.get("role"),
        "action": event.get("action"),
        "timestamp": time.time(),
        "risk_score": event.get("risk_score"),
        "flags": event.get("flags")
    }
    logging.info(f"AUDIT_LOG: {log_entry}")
    return log_entry

class LLMOpsTracker:
    def record(self, txn_id, stage_times, flags):
        metrics = {
            "txn_id": txn_id,
            "retrieval_time": stage_times.get("retrieval_time", 0),
            "reasoning_time": stage_times.get("reasoning_time", 0),
            "validation_time": stage_times.get("validation_time", 0),
            "total_flags": len(flags),
            "timestamp": time.time()
        }
        logging.info(f"LLMOps Metrics: {metrics}")
        return metrics

llmops = LLMOpsTracker()

# COMMAND ----------

# ============================================
# AI LINEAGE TRACKER
# ============================================

class AILineageTracker:
    def __init__(self):
        self.events = []

    def log(self, stage, input_data, output_data):
        entry = {
            "stage": stage,
            "timestamp": time.time(),
            "input": str(input_data),
            "output": str(output_data)
        }
        self.events.append(entry)
        logging.info(f"AI_LINEAGE: {entry}")

    def get(self):
        return self.events

ai_lineage = AILineageTracker()

# COMMAND ----------

# ============================================
# BRONZE LAYER (RAW INGESTION)
# ============================================

# Simulated raw transaction data
data = [
 ("TXN001","C001",15000,"Singapore"),
 ("TXN002","C002",500,"Singapore"),
 ("TXN003","C003",25000,"Nigeria"),
 ("TXN004","C004",8000,"India"),
 ("TXN005","C005",12000,"North Korea")
]

columns = ["txn_id","customer_id","amount","country"]

# Create Spark DataFrame
bronze_df = spark.createDataFrame(data, columns)

display(bronze_df)

# COMMAND ----------

# ============================================
# SILVER LAYER (DATA CLEANING)
# ============================================

# from pyspark.sql.functions import col

silver_df = bronze_df \
    .filter(col("amount") > 0) \
    .dropDuplicates(["txn_id"])

display(silver_df)

# COMMAND ----------

# ============================================
# GOLD LAYER (BUSINESS LOGIC)
# ============================================
# from pyspark.sql.functions import col, when

gold_df = silver_df.withColumn(
    "risk_score",
    when(col("amount") > 20000, 3)
    .when(col("amount") > 10000, 2)
    .otherwise(1)
    +
    when(col("country").isin("North Korea", "Nigeria"), 3).otherwise(0)
).withColumn(
    "risk_category",
    when(col("risk_score") >= 2, "High").otherwise("Low")
)

display(gold_df)

# COMMAND ----------

# ============================================
# RAG KNOWLEDGE BASE
# ============================================

policy_docs = [
    "Transactions above 10000 must be flagged",
    "Sanctioned countries require enhanced due diligence",
    "Frequent transfers indicate structuring risk",
    "Crypto transactions require monitoring"
]

model = SentenceTransformer("all-MiniLM-L6-v2")
doc_embeddings = np.array(model.encode(policy_docs)).astype("float32")
index = faiss.IndexFlatL2(doc_embeddings.shape[1])
index.add(doc_embeddings)

def retrieve(query, top_k=2):
    q_emb = np.array(model.encode([query])).astype("float32")
    _, idx = index.search(q_emb, top_k)
    return [policy_docs[i] for i in idx[0]]

# COMMAND ----------

# ============================================
# MCP TOOL REGISTRY
# ============================================

class MCPToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, name, fn):
        self.tools[name] = fn

    def call(self, name, *args, **kwargs):
        return self.tools[name](*args, **kwargs)

tool_registry = MCPToolRegistry()
tool_registry.register("retrieval_tool", retrieve)

# COMMAND ----------

# ============================================
# MCP AGENTS
# ============================================

class MCPContext:
    def __init__(self, txn, query, role):
        self.txn = txn
        self.query = query
        self.role = role
        self.memory = {}
        self.agent_outputs = {}
        self.metadata = {}

    def update(self, key, value):
        self.memory[key] = value


class MCPRetrieverAgent:
    def run(self, context):
        start = time.time()
        docs = tool_registry.call("retrieval_tool", context.query)
        context.update("retrieved_docs", docs)
        ai_lineage.log("retrieval", {"query": context.query}, {"docs": docs})
        context.metadata["retrieval_time"] = time.time() - start
        return context


class MCPReasonerAgent:
    def run(self, context):
        start = time.time()
        docs = context.memory.get("retrieved_docs", [])
        result = {
            "txn_id": context.txn["txn_id"],
            "decision_basis": docs,
            "risk_factors": ["High Value Transaction"] if context.txn.get("amount", 0) > 10000 else [],
            "policy_references": docs,
            "summary": "Transaction exceeds AML threshold" if context.txn.get("amount", 0) > 10000 else "AML evaluation completed"
        }
        context.agent_outputs["reasoning"] = result
        ai_lineage.log("reasoning", {"txn_id": context.txn["txn_id"], "docs": docs}, {"reasoning": result})
        context.metadata["reasoning_time"] = time.time() - start
        return context


class MCPValidatorAgent:
    def run(self, context):
        start = time.time()
        txn = context.txn
        flags = []
        rule_hits = {"high_value": False, "sanctioned_country": False, "policy_triggered": False}

        if txn["amount"] > 10000:
            flags.append("High Value")
            rule_hits["high_value"] = True

        if txn["country"] in ["North Korea", "Nigeria"]:
            flags.append("Sanctioned")
            rule_hits["sanctioned_country"] = True

        if "sanction" in " ".join(context.memory.get("retrieved_docs", [])).lower():
            flags.append("Policy Triggered")
            rule_hits["policy_triggered"] = True

        confidence = "High" if len(flags) >= 2 else "Medium" if len(flags) == 1 else "Low"
        validation_result = {"flags": flags, "confidence": confidence, "rule_hits": rule_hits}

        context.agent_outputs["validation"] = validation_result
        context.agent_outputs["flags"] = flags
        context.agent_outputs["confidence"] = confidence

        ai_lineage.log("validation", {"txn": txn}, validation_result)
        context.metadata["validation_time"] = time.time() - start
        return context

# COMMAND ----------

# ============================================
# AGENT ROUTER + ORCHESTRATOR
# ============================================

class AgentRouter:
    def route(self, txn):
        route = ["retriever"]
        if txn["amount"] > 10000 or txn.get("risk_score", 0) >= 2:
            route += ["reasoner", "validator"]
        return route


class MCPRiskOrchestrator:
    def __init__(self):
        self.router = AgentRouter()
        self.retriever = MCPRetrieverAgent()
        self.reasoner = MCPReasonerAgent()
        self.validator = MCPValidatorAgent()
        self.llmops = LLMOpsTracker()

    def run(self, txn, query, role="analyst"):

        if not prompt_injection_guard(query)["allowed"]:
            return {"status": "BLOCKED", "reason": "Injection detected"}

        if not unsafe_query_filter(query)["allowed"]:
            return {"status": "BLOCKED", "reason": "Unsafe query"}

        if not check_access(role, "view_risk"):
            return {"status": "ACCESS_DENIED"}

        txn = mask_sensitive_data(txn)
        context = MCPContext(txn, query, role)
        route = self.router.route(txn)
        context.update("route", route)

        if "retriever" in route:
            context = self.retriever.run(context)
        if "reasoner" in route:
            context = self.reasoner.run(context)
        if "validator" in route:
            context = self.validator.run(context)

        flags      = context.agent_outputs.get("flags", [])
        confidence = context.agent_outputs.get("confidence", "Low")
        risk_score = txn.get("risk_score", 0)
        risk_band  = "High" if risk_score >= 2 else "Low"

        metrics = self.llmops.record(
            txn["txn_id"],
            {
                "retrieval_time":  context.metadata.get("retrieval_time", 0),
                "reasoning_time":  context.metadata.get("reasoning_time", 0),
                "validation_time": context.metadata.get("validation_time", 0),
            },
            flags
        )

        audit_log({
            "txn_id": txn["txn_id"], "role": role,
            "action": "AML_ANALYSIS", "risk_score": risk_score, "flags": flags
        })

        ai_lineage.log(
            "final_decision",
            {"txn": txn, "route": route},
            {"flags": flags, "risk_score": risk_score, "confidence": confidence, "risk_band": risk_band}
        )

        reasoning_output = context.agent_outputs.get("reasoning") if check_access(role, "view_reasoning") else None

        return {
            "status":     "SUCCESS",
            "txn":        txn,
            "route":      route,
            "docs":       context.memory.get("retrieved_docs", []),
            "reasoning":  reasoning_output,
            "validation": context.agent_outputs.get("validation"),
            "flags":      flags,
            "confidence": confidence,
            "risk_score": risk_score,
            "risk_band":  risk_band,
            "metrics":    metrics,
            "ai_lineage": ai_lineage.get()
        }

# COMMAND ----------

# ============================================
# EXECUTION
# ============================================

txn = gold_df.toPandas().iloc[0].to_dict()
query = "Analyze AML risk for high value transaction"

orchestrator = MCPRiskOrchestrator()
result = orchestrator.run(txn, query, role="compliance_officer")

display(result)

# COMMAND ----------

import json

# Run orchestrator on ALL transactions
full_results = []
transactions = gold_df.toPandas().to_dict(orient="records")

for txn in transactions:
    query = "Analyze AML risk for high value transaction"
    result = orchestrator.run(txn, query, role="compliance_officer")
    
    # Clean ai_lineage
    if "ai_lineage" in result:
        for entry in result["ai_lineage"]:
            entry["input"] = str(entry["input"])
            entry["output"] = str(entry["output"])
    
    full_results.append(result)

print(f"✅ Processed {len(full_results)} transactions")

# COMMAND ----------

import json
import base64
from IPython.display import HTML, display

json_str = json.dumps(full_results, indent=2, default=str)
b64 = base64.b64encode(json_str.encode()).decode()

download_html = f'''
<script>
function downloadJSON() {{
    const data = atob("{b64}");
    const blob = new Blob([data], {{type: "application/octet-stream"}});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "aml_full_results.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}}
</script>
<button onclick="downloadJSON()" style="
    background-color: #4CAF50;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 5px;
    cursor: pointer;
    font-size: 14px;">
    ⬇️ Download aml_full_results.json
</button>
'''

display(HTML(download_html))