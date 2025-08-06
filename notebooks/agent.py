# Databricks notebook source
# MAGIC %md
# MAGIC There are 2 notebooks as part of a set to build a RAG agent:
# MAGIC 1. [**agent**]($./agent): contains the code to build the agent (only the code in `mlflow.models.set_model` will be served)
# MAGIC 2. [driver]($./driver): references the agent code then logs, registers, evaluates and deploys the agent.
# MAGIC
# MAGIC ## Prerequisites
# MAGIC 1. Create the Vector Store in [0_setup]($./0_setup)
# MAGIC 2. Check  [config.yml]($./config.yml) settings
# MAGIC
# MAGIC ## Next steps
# MAGIC After testing and iterating on your agent in this notebook, go to the auto-generated [driver]($./driver) notebook in this folder to log, register, evaluate, and deploy the agent.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

# MAGIC %pip install -U langchain langchain_core mlflow-skinny==3.2.0 databricks-langchain databricks-vectorsearch
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %pip freeze

# COMMAND ----------

def extract_user_query_string(chat_messages_array):
    return chat_messages_array[-1]["content"]

# COMMAND ----------

# MAGIC %md
# MAGIC Use `mlflow.langchain.autolog()` to set up [MLflow traces](https://docs.databricks.com/en/mlflow/mlflow-tracing.html).

# COMMAND ----------

import mlflow
from mlflow.models import ModelConfig

mlflow.langchain.autolog()
config = ModelConfig(development_config="config.yml")
config.to_dict()

# COMMAND ----------

query = "Can you give me some troubleshooting steps for SoundWave X5 Pro Headphones that won't connect?"

# COMMAND ----------

# MAGIC %md
# MAGIC ### Create the retriever chain
# MAGIC Specify:
# MAGIC 1. the LLM receiving the question
# MAGIC 2. the retriever (assumes you have set up a Vector Store earlier in [0_setup]($./0_setup))
# MAGIC 3. system prompt
# MAGIC 4. helper functions to format the input/output [OPTIONAL]

# COMMAND ----------

from databricks_langchain import ChatDatabricks

llm = ChatDatabricks(endpoint=config.get("llm_endpoint"))

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient
from databricks_langchain.vectorstores import DatabricksVectorSearch
import mlflow

vector_search_as_retriever = DatabricksVectorSearch(
    endpoint=config.get('retriever')['vs_endpoint'],
    index_name=config.get('retriever')['vs_index'],
    columns=[
      "product_category",
      "product_sub_category",
      "product_name",
      "product_doc",
      "product_id",
      "indexed_doc"
    ],
).as_retriever(search_kwargs={"k": config.get('retriever')['k']})

# Set retriever schema to be returned
# Map the column names in the returned table to MLflow's expected fields: primary_key, text_column, and doc_uri
mlflow.models.set_retriever_schema(
    primary_key="product_id",
    text_column="indexed_doc",
    doc_uri="product_id",
    name=config.get('retriever')['vs_index'],
)

# COMMAND ----------

# MAGIC %md
# MAGIC Test retrieval without system prompt. Just retrieves without summarization

# COMMAND ----------

relevant_docs = vector_search_as_retriever.invoke(query)
relevant_docs

# COMMAND ----------

from langchain_core.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from operator import itemgetter

prompt = ChatPromptTemplate.from_messages(
    [
        (  # System prompt contains the instructions
            "system",
            """You are an assistant that answers questions. Use the following pieces of retrieved context to answer the question. Be concise and answer in less than 200 words. Some pieces of context may be irrelevant, in which case you should not use them to form the answer.

Context: {context}""",
        ),
        (
            "user", "{question}"
        ),
    ]
)

chain = (
    {
        "question": itemgetter("messages") | RunnableLambda(extract_user_query_string),
        "context": itemgetter("messages")
        | RunnableLambda(extract_user_query_string)
        | vector_search_as_retriever
    }
    | prompt
    | llm
    | StrOutputParser()
)

# COMMAND ----------

chain.invoke({"messages": [{"role": "user", "content": query}]})

# COMMAND ----------

# The defines the object (i.e. agent) that will be logged in the driver NB even if the driver NB references this entire agent NB.
mlflow.models.set_model(chain)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next steps
# MAGIC
# MAGIC You can rerun the cells above to iterate and test the agent.
# MAGIC
# MAGIC Go to the auto-generated [driver]($./driver) notebook in this folder to log, register, and deploy the agent.