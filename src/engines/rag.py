import json
import random
import time
import math
import re
import os
import sys

# Import RealLLM for actual API integration
try:
    from llm_client import RealLLM
except ImportError:
    try:
        from .llm_client import RealLLM
    except ImportError:
        RealLLM = None

# Hack to allow importing config from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from config import config
except ImportError:
    class Config:
        def __init__(self):
            self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
    config = Config()

class RAGEngine:
    def __init__(self, schema_file="data/schema.json", schema_dict=None, api_key=None):
        self.name = "Generic RAG"
        if schema_dict:
            self.schema = schema_dict
        else:
            self.schema_file = schema_file or "data/schema.json"
            with open(self.schema_file, 'r') as f:
                self.schema = json.load(f)

        # Simulate simple "Embeddings" by just using TF-IDF logic or basic string matching
        self.embeddings = {}
        for table, details in self.schema.items():
            text = f"{table} " + " ".join(details['columns']) + " " + details.get('description', '')
            self.embeddings[table] = text.lower()

        self.llm = None
        key_to_use = api_key or config.openai_api_key
        if key_to_use and RealLLM:
             try:
                self.llm = RealLLM(key_to_use)
             except Exception as e:
                pass

    def process(self, query):
        """
        Simulates retrieving the top-k most similar tables based on embedding similarity.
        Then asks an "LLM" (simulated or real) to pick columns.
        """
        query_str = query.lower()
        query_words = set(query_str.split())

        scored_tables = []
        for table, text in self.embeddings.items():
            # Jaccard similarity simulation for RAG retrieval
            doc_words = set(text.split())
            score = len(query_words & doc_words) / len(query_words | doc_words) if len(query_words | doc_words) > 0 else 0
            scored_tables.append((score, table))

        scored_tables.sort(key=lambda x: x[0], reverse=True)
        top_k_tables = [t[1] for t in scored_tables[:3]] # Retrieve Top 3

        selected_columns = []

        if self.llm:
            # Use Real LLM for Baseline too if available
            for table in top_k_tables:
                cols = self.schema[table]['columns']
                chosen = self.llm.select_columns(query, table, cols)
                if chosen and isinstance(chosen, list):
                    selected_columns.extend(chosen)
                else:
                    # Fallback if LLM returns bad data
                    for col in cols:
                        if any(word in col.lower() for word in query_words):
                             selected_columns.append(col)
        else:
            # Naive Logic
            for table in top_k_tables:
                for col in self.schema[table]['columns']:
                    if any(word in col.lower() for word in query_words):
                        selected_columns.append(col)

        return {
            "tables": top_k_tables,
            "columns": list(set(selected_columns)),
            "filters": []
        }
