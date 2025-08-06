# Databricks notebook source
# MAGIC %md
# MAGIC There are 2 notebooks as part of a set to build a RAG agent:
# MAGIC 1. [agent]($./agent): contains the code to build the agent (only the code in `mlflow.models.set_model` will be served)
# MAGIC 2. [**driver**]($./driver): references the agent code then logs, registers, evaluates and deploys the agent.
# MAGIC
# MAGIC ## Prerequisites
# MAGIC 1. Create the Vector Store in [0_setup]($./0_setup)
# MAGIC 2. Check  [config.yml]($./config.yml) settings
# MAGIC 3. Check that the agent is defined in [agent]($./agent) NB.
# MAGIC
# MAGIC ## Next steps
# MAGIC Go to Serving to test your deployed agent.
# MAGIC
# MAGIC ## Setup

# COMMAND ----------

# MAGIC %pip install -U langchain==0.3.26 langchain_core mlflow-skinny==3.2.0 databricks-langchain==0.6.0 databricks-vectorsearch>=0.57 databricks-agents
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %pip freeze

# COMMAND ----------

import mlflow

def get_latest_model_version(model_name):
    from mlflow.tracking import MlflowClient
    mlflow_client = MlflowClient(registry_uri="databricks-uc")
    latest_version = 1
    for mv in mlflow_client.search_model_versions(f"name='{model_name}'"):
        version_int = int(mv.version)
        if version_int > latest_version:
            latest_version = version_int
    return latest_version

# COMMAND ----------

from mlflow.models import ModelConfig

mlflow.langchain.autolog()
mlflow.set_registry_uri('databricks-uc')

config = ModelConfig(development_config="config.yml")
config.to_dict()

# COMMAND ----------

catalog_name = config.get("catalog")
schema_name = config.get("schema")
model_name = "customer_service"

registered_name = f"{catalog_name}.{schema_name}.{model_name}"
artifact_path = "agent"

# COMMAND ----------

query = "Can you give me some troubleshooting steps for SoundWave X5 Pro Headphones that won't connect?"
input_example = {
    "messages": [
        {
            "role": "user",
            "content": query
        }
    ]
}

# COMMAND ----------

# MAGIC %md
# MAGIC ### Log the `agent` as an MLflow model
# MAGIC Log the agent as code from the [agent]($./agent) notebook. See [MLflow - Models from Code](https://mlflow.org/docs/latest/models.html#models-from-code).

# COMMAND ----------

# Log the model to MLflow
import os
from mlflow.models.resources import (
    DatabricksVectorSearchIndex, 
    DatabricksServingEndpoint
)

with mlflow.start_run():
    logged_agent_info = mlflow.langchain.log_model(
        # in agent_noextras, VS is code, not a fn
        lc_model=os.path.join(os.getcwd(), 'agent'),
        name=artifact_path,
        registered_model_name=registered_name,
        model_config="config.yml",
        pip_requirements=[
            "langchain==0.3.26",
            "databricks_langchain==0.6.0",
            "databricks-vectorsearch==0.57",
            "ipython"
        ],
        input_example=input_example,
        # specify resources for deployed server to have explicit access
        resources=[
            DatabricksServingEndpoint(endpoint_name=config.get("llm_endpoint")),
            DatabricksVectorSearchIndex(index_name=config.get('retriever')['vs_index'])
        ]
    )

# COMMAND ----------

model_uri = f"runs:/{logged_agent_info.run_id}/{artifact_path}"
#model_uri = 'runs:/dcbafcab5ac84d73bb100709690d1579/agent'

# COMMAND ----------

# MAGIC %md
# MAGIC ## Deploy the agent

# COMMAND ----------

latest_version = get_latest_model_version(registered_name)
latest_version

# COMMAND ----------

from databricks import agents

# Deploy the model to the review app and a model serving endpoint
agents.deploy(model_name=registered_name, 
              model_version=latest_version,
              workload_size="Large",
              scale_to_zero=False,
              tags = {"endpointSource": "playground"})

# COMMAND ----------

# MAGIC %md
# MAGIC ## [OPTIONAL] For testing inferencing locally
# MAGIC Useful to test inferencing before remote deployment

# COMMAND ----------

# Test a question best answered by the retriever
loaded_model = mlflow.langchain.load_model(model_uri)
loaded_model.invoke(input_example)