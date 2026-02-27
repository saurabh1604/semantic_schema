import json
import os
try:
    from ..llm_client import RealLLM
except ImportError:
    RealLLM = None

class BaseEngine:
    def __init__(self, schema_file="data/schema.json", schema_dict=None, api_key=None, model="gpt-4o"):
        import json # Re-import inside just in case
        if schema_dict:
            self.schema = schema_dict
        else:
            self.schema_file = schema_file or "data/schema.json"
            if os.path.exists(self.schema_file):
                with open(self.schema_file, 'r') as f:
                    self.schema = json.load(f)
            else:
                self.schema = {}

        self.model = model
        self.llm = None
        if api_key and RealLLM:
             try:
                self.llm = RealLLM(api_key, model=self.model)
             except Exception:
                pass

    def process(self, query):
        raise NotImplementedError
