This uses [`locust`](https://locust.io/) which fires up a flask web app which isn't supported on Databricks Workspace. Please run it on your local laptop or cloud instance that can access the Databricks endpoint you are load testing.

## Setup
1. Clone the repo
```
git clone git@github.com:yenlow/load-test.git
cd load-test
chmod +x *.sh
```
2. Create and activate a virtual environment:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```
4. Check that you are running the python in the activated venv.
```bash
locust -h
```

Also check out the Databricks Model Serving limits [here](https://docs.databricks.com/aws/en/machine-learning/model-serving/model-serving-limits).

--------------------------
## Usage:
### 1. **PDF parsing to markdown with `pymupdf4llm`**
```
python file_processor.py -i docs -n 6
```
- Place your PDF files in a folder (e.g., `docs`)
- Converts 5 randomly selected PDF files from the input folder e.g., `docs` to markdown using multi-threaded parallel processing e.g. `-n 6` for 6 cores
- Detects images, tables, links, and formatting
- The script will create a `markdown_output` folder containing:
```
markdown_output/
├── <individual>.md
├── all_documents.md
├── features.json
└── processing_results.json
```
| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--input-folder` | `-i` | Path to folder containing PDF files | **Required** |
| `--output-folder` | `-o` | Path to folder for markdown output | `markdown_output` |
| `--max-workers` | `-n` | Number of worker threads for parallel processing | `1` |

### 2. **Load testing LLM (without RAG) with `locust`**
```
locust -f load-test/local_load_test/load_test.py -i markdown_output/features.json
```
*The input file set by `-i` should be the output `features.json` from PDF parsing step in #1*

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--infile` | `-i` | Path to json with the input to LLM in a messages format. See example [features.json](load-test/local_load_test/features.json) | local_load_test/features.json |
| `--endpoint-name` | `-e` | LLM endpoint on Databricks | databricks-claude-3-7-sonnet |
| `--token` |  | Databricks token | [redacted] |
See locust [README.md](load-test/local_load_test/README.md)


### 3. **Load testing RAG agent endpoint with `locust`**
This requires a RAG agent already served on a Databricks endpoint. To serve the agent, download and import [notebooks](notebooks) into Databricks to first build and deploy a RAG agent.

```
locust -f load-test/local_load_test/load_test.py -i query.json -e agents_yen_customers-banner_loadtest-customer_service
```
The input file here will be simply a question in the messages format without any context as that will be provided at runtime by the RAG agent.

The endpoint should be the RAG agent deployed on Model Serving in Databricks.

### 4. [OPTIONAL] Separately time Step #1
```
./time_file_processor.sh 100
```
It will call Step #1 `python file_processor.py` 100 times and time it with full statistics. Edit CMD in line 23 as needed.

The times will depend on where you deploy the parsing code and whether it supports multi-threaded processing. This step is unlikely to be the bottleneck and should not affect load tests.


## Troubleshooting
**Error 400:** Check that your input to the endpoint follows a messages format
```
{
  "messages": [
    {
      "role": "user",
      "content": "How do I clear paper jams in the copier?"
    }
  ]
}
```


**Error 200:** Authentication issues
Check that you can access the endpoint you are load testing
```
curl \
  -u token:yourtoken \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"messages": [
    {
      "role": "user",
      "content": "How do I clear paper jams in the copier?"
    }
  ]}' \
  https://your_databricks_host/serving-endpoints/your_endpoint_name/invocations 
```
