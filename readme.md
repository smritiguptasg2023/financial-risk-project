# GenAI AML Risk Detection System

## Overview
This project is a GenAI-based AML (Anti-Money Laundering) risk detection system using:
- Multi-Agent architecture
- RAG (FAISS-based retrieval)
- Databricks Medallion pipeline
- FastAPI backend
- Rule-based + AI hybrid reasoning

---

## Files

- app.py → Main GenAI system (API + agents + RAG)
- databricks_pipeline.py → Data pipeline (Bronze / Silver / Gold)
- rca_document.pdf → Failure analysis and mitigation

---

## Tech Stack
Python, FastAPI, Pandas, PySpark, FAISS, Sentence Transformers

---

## How to Run
pip install -r requirements.txt  
python app.py