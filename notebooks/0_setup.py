# Databricks notebook source
# MAGIC %md
# MAGIC # Setup (only run once)
# MAGIC 1. Makes a copy of the required tables to avoid deletion
# MAGIC 2. Makes a VS endpoint and index from a delta table

# COMMAND ----------

# MAGIC %pip install mlflow-skinny databricks_langchain
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

from mlflow.models import ModelConfig

config = ModelConfig(development_config="config.yml")
config.to_dict()

# COMMAND ----------

catalog_name = config.get('catalog')
schema_name = config.get('schema')

spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog_name}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog_name}.{schema_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Make a copy of the required tables
# MAGIC In case they get deleted

# COMMAND ----------

spark.sql(f"DROP TABLE IF EXISTS {catalog_name}.{schema_name}.product_docs")
spark.sql(f"""
    CREATE TABLE {catalog_name}.{schema_name}.product_docs AS 
    SELECT * FROM retail_prod.agents.product_docs
""")

# COMMAND ----------

# MAGIC %sql
# MAGIC SHOW TBLPROPERTIES yen_customers.banner_loadtest.product_docs

# COMMAND ----------

spark.sql(f"""
ALTER TABLE {catalog_name}.{schema_name}.product_docs SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create the Vector Store endpoint and index from the source delta table
# MAGIC See more in this [VS guide](https://docs.databricks.com/aws/en/generative-ai/create-query-vector-search)

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient

client = VectorSearchClient()

# Create VS endpoint
# Check if the endpoint already exists
endpoints = client.list_endpoints()
endpoint_name = config.get('retriever')['vs_endpoint']
if endpoint_name not in [ep.get('name') for ep in endpoints['endpoints']]:
    # Create VS endpoint
    client.create_endpoint(
        name=endpoint_name,
        endpoint_type="STANDARD"
    )

# Create VS index
index = client.create_delta_sync_index(
  endpoint_name=config.get('retriever')['vs_endpoint'],
  source_table_name=config.get('retriever')['vs_source'],
  index_name=config.get('retriever')['vs_index'],
  pipeline_type="TRIGGERED",
  primary_key="product_id",
  embedding_source_column="product_doc",
  embedding_model_endpoint_name="databricks-gte-large-en"
)

# COMMAND ----------

