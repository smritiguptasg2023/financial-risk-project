# Databricks notebook source
data = [
("TXN001","C001","2026-04-20",12000,"Singapore","transfer","online","investment",5),
("TXN002","C002","2026-04-20",500,"Singapore","payment","online","retail",1),
("TXN003","C003","2026-04-21",25000,"Nigeria","transfer","branch","unknown",2),
("TXN004","C004","2026-04-21",8000,"India","withdrawal","ATM","cash",10),
("TXN005","C005","2026-04-22",15000,"North Korea","transfer","online","crypto",1)
]

columns = ["transaction_id","customer_id","transaction_date","amount",
"country","transaction_type","channel","merchant_category",
"previous_txn_count_24h"]

bronze_df = spark.createDataFrame(data, columns)
bronze_df.show()

# COMMAND ----------

bronze_df.write.mode("overwrite").saveAsTable("bronze_transactions")

# COMMAND ----------

# MAGIC %sql
# MAGIC select * from bronze_transactions

# COMMAND ----------

from pyspark.sql.functions import col, to_date

silver_df = bronze_df \
    .withColumn("transaction_date", to_date(col("transaction_date"))) \
    .filter(col("amount") > 0) \
    .dropDuplicates(["transaction_id"])

silver_df.show()


# COMMAND ----------

silver_df.write.mode("overwrite").saveAsTable("silver_transactions")

# COMMAND ----------

# MAGIC %sql
# MAGIC select * from silver_transactions

# COMMAND ----------

from pyspark.sql.functions import when

gold_df = silver_df \
    .withColumn("risk_score",
        when(col("amount") > 10000, 2).otherwise(0) +
        when(col("country").isin("North Korea","Nigeria"), 3).otherwise(0) +
        when(col("previous_txn_count_24h") > 5, 2).otherwise(0) +
        when(col("merchant_category").isin("crypto","investment"), 1).otherwise(0)
    )

# COMMAND ----------

gold_df = gold_df.withColumn("risk_category",
    when(col("risk_score") >= 5, "High")
    .when(col("risk_score") >= 3, "Medium")
    .otherwise("Low")
)

gold_df.show()

# COMMAND ----------

gold_df.write.mode("overwrite").saveAsTable("gold_transactions")

# COMMAND ----------

# MAGIC %sql
# MAGIC select * from gold_transactions

# COMMAND ----------

# aml_text = """
# Transactions above $10,000 must be monitored.
# High-risk countries must trigger review.
# Frequent transactions indicate structuring risk.
# Crypto transactions require enhanced due diligence.
# """

# COMMAND ----------

# chunks = aml_text.split(".")
# print(chunks)
# chunks = [c.strip() for c in chunks if c.strip() != ""]
# print(chunks)

# COMMAND ----------

# %pip install sentence-transformers

# COMMAND ----------

# from sentence_transformers import SentenceTransformer

# COMMAND ----------

# model = SentenceTransformer('all-MiniLM-L6-v2')
# embeddings = model.encode(chunks)
# print(embeddings[0])

# COMMAND ----------

# vector_store = list(zip(chunks, embeddings))
# print(vector_store)

# COMMAND ----------

# def retrieve(query):
#     # simple keyword match (since no real vector search)
#     results = []
#     for chunk, emb in vector_store:
#         if any(word.lower() in chunk.lower() for word in query.split()):
#             results.append(chunk)
#     return results[:2]

# COMMAND ----------

# def generate_answer(query):
#     context = retrieve(query)
#     # print(context)
#     context_text = " ".join(context)
#     # print(context_text)
    
#     response = f"""
#     Based on policy:
#     {context_text}
    
#     Answer:
#     The transaction is considered risky because it aligns with the above compliance rules.
#     """
    
#     return response

# COMMAND ----------

# Transactions above $10,000 must be monitored.
# High-risk countries must trigger review.
# Frequent transactions indicate structuring risk.
# Crypto transactions require enhanced due diligence.

# COMMAND ----------

# query = "Why is this transaction high risk?"
# print(generate_answer(query))

# COMMAND ----------

# generate_answer("Transaction above 10000 from high risk country")