import json
from locust import events, HttpUser, task


# Retrieve command line arguments
# Locust docs: https://docs.locust.io/en/stable/extending-locust.html?highlight=event#custom-arguments
@events.init_command_line_parser.add_listener
def _(parser):
    parser.add_argument("--endpoint-name", "-e", default="databricks-claude-3-7-sonnet")
    parser.add_argument(
        "--token",
        is_secret=True,
        # default="save_taken_here",
    )
    parser.add_argument("--infile", "-i", default="local_load_test/features.json")


class LoadTestUser(HttpUser):

    @task
    def query_single_model(self):
        # Reads features from JSON file. Format expected by Databricks Model Serving
        # explained here: https://docs.databricks.com/machine-learning/model-serving/create-manage-serving-endpoints.html#request-format
        infile = self.environment.parsed_options.infile
        token = self.environment.parsed_options.token
        endpoint_name = self.environment.parsed_options.endpoint_name

        with open(infile, "r") as json_features:
            model_input = json.load(json_features)

        headers = {"Authorization": f"Bearer {token}"}

        self.client.post(
            f"/serving-endpoints/{endpoint_name}/invocations",
            headers=headers,
            json=model_input,
        )
