from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

with open("aml_full_results.json") as f:
    data = json.load(f)

@app.get("/")
def root():
    return {"message": "AML Risk API is running", "total_transactions": len(data)}

@app.get("/transactions")
def get_all_transactions():
    return data

@app.get("/transaction/{txn_id}")
def get_transaction(txn_id: str):
    result = next((r for r in data if r.get("txn", {}).get("txn_id") == txn_id), None)
    if not result:
        raise HTTPException(status_code=404, detail=f"Transaction {txn_id} not found")
    return result

@app.get("/flags")
def get_flagged_transactions():
    return [r for r in data if r.get("risk_band") == "High"]

@app.get("/metrics")
def get_llmops_metrics():
    return [r.get("metrics", {}) for r in data]

@app.get("/lineage/{txn_id}")
def get_lineage(txn_id: str):
    result = next((r for r in data if r.get("txn", {}).get("txn_id") == txn_id), None)
    if not result:
        raise HTTPException(status_code=404, detail=f"Transaction {txn_id} not found")
    return result.get("ai_lineage", [])

@app.get("/reasoning/{txn_id}")
def get_reasoning(txn_id: str):
    result = next((r for r in data if r.get("txn", {}).get("txn_id") == txn_id), None)
    if not result:
        raise HTTPException(status_code=404, detail=f"Transaction {txn_id} not found")
    return result.get("reasoning", {})

@app.get("/summary")
def get_summary():
    total = len(data)
    high_risk = len([r for r in data if r.get("risk_band") == "High"])
    flagged = len([r for r in data if r.get("flags")])
    avg_retrieval = sum(
        r.get("metrics", {}).get("retrieval_time", 0) for r in data
    ) / total if total > 0 else 0
    return {
        "total_transactions": total,
        "high_risk_count": high_risk,
        "flagged_count": flagged,
        "low_risk_count": total - high_risk,
        "avg_retrieval_time_ms": round(avg_retrieval * 1000, 2)
    }

@app.get("/dashboard", response_class=FileResponse)
def get_dashboard():
    return FileResponse("dashboard.html", media_type="text/html")