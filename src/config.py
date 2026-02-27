import os
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
class Config:
    def __init__(self):
        # Primary source: Environment Variable or .env file
        # USER INSTRUCTION: If load_dotenv doesn't work for you,
        # replace the empty string below with your actual API key:
        # self.openai_api_key = "sk-..."
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")

        # Debug Print to confirm detection (check terminal logs)
        if self.openai_api_key:
            print(f"[DEBUG] Config loaded API Key (Length: {len(self.openai_api_key)})")
        else:
            print("[DEBUG] Config: No API Key found in env vars.")

        self.data_dir = "data"
        self.schema_file = os.path.join(self.data_dir, "schema.json")
        self.cbo_file = os.path.join(self.data_dir, "cbo_stats.json")
        self.logs_file = os.path.join(self.data_dir, "query_logs.json")

    def set_openai_key(self, key):
        self.openai_api_key = key
        os.environ["OPENAI_API_KEY"] = key

config = Config()
