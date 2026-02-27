import os
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
class Config:
    def __init__(self):
        # Primary source: Environment Variable or .env file
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")

        self.data_dir = "data"
        self.schema_file = os.path.join(self.data_dir, "schema.json")
        self.cbo_file = os.path.join(self.data_dir, "cbo_stats.json")
        self.logs_file = os.path.join(self.data_dir, "query_logs.json")

    def set_openai_key(self, key):
        self.openai_api_key = key
        os.environ["OPENAI_API_KEY"] = key

config = Config()
