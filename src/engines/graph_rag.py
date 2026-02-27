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

class GraphEngine:
    def __init__(self, schema_file="data/schema.json", schema_dict=None):
        if schema_dict:
            self.schema = schema_dict
        else:
            self.schema_file = schema_file or "data/schema.json"
            with open(self.schema_file, 'r') as f:
                self.schema = json.load(f)

        # Build a simple graph: Bidirectional Adjacency List
        self.adj_list = {}
        for table, details in self.schema.items():
            if table not in self.adj_list:
                self.adj_list[table] = []

            for fk_col, target in details.get('foreign_keys', {}).items():
                target_table = target.split('.')[0]
                if target_table not in self.adj_list:
                    self.adj_list[target_table] = []
                self.adj_list[table].append(target_table)
                self.adj_list[target_table].append(table)

        self.llm = None
        if config.openai_api_key and RealLLM:
             try:
                self.llm = RealLLM(config.openai_api_key)
             except Exception as e:
                pass

    def process(self, query):
        """
        1. Find "Seed" tables (via LLM or Fuzzy Match).
        2. Expand to find a connected path (Steiner Tree simulation).
        """
        start_time = time.time()

        # Step 1: Find Seeds
        seed_tables = []

        if self.llm:
            # Use LLM for semantic seed selection (GraphRAG)
            # Limit context size
            schema_keys = list(self.schema.keys())[:50]
            schema_summary = "\n".join([f"{t}: {self.schema[t].get('description', '')}" for t in schema_keys])
            extracted = self.llm.extract_entities(query, schema_summary)
            seed_tables = [t for t in extracted if t in self.schema]

        # Fallback / Augment with Heuristic if LLM missed or unavailable
        if not seed_tables:
            query_lower = query.lower()
            query_words = set(query_lower.split())

            for table in self.schema:
                table_lower = table.lower()
                if any(part in query_lower for part in table_lower.split('_') if len(part) > 3):
                    seed_tables.append(table)
                else:
                    table_tokens = set(table_lower.split('_'))
                    if table_tokens & query_words:
                         seed_tables.append(table)

        seed_tables = list(set(seed_tables))

        # Step 2: Traverse Graph (Simulated Steiner Tree / Path Finding)
        if len(seed_tables) >= 2:
            # Try to connect the first two seeds
            path = self._find_shortest_path(seed_tables[0], seed_tables[1])
            if path:
                seed_tables.extend(path)

        # Step 3: Select columns from the connected tables
        selected_columns = []
        for table in set(seed_tables):
            if table in self.schema:
                # Basic fuzzy match for columns if no LLM for col selection
                query_lower = query.lower()
                for col in self.schema[table]['columns']:
                    col_lower = col.lower()
                    if col_lower in query_lower or any(part in query_lower for part in col_lower.split('_') if len(part) > 3):
                        selected_columns.append(col)

        return {
            "tables": list(set(seed_tables)),
            "columns": list(set(selected_columns)),
            "filters": [],
            "execution_time": time.time() - start_time
        }

    def _find_shortest_path(self, start, end):
        # Simple BFS
        queue = [(start, [start])]
        visited = set()
        while queue:
            if not queue: break

            (vertex, path) = queue.pop(0)
            if vertex not in visited:
                if vertex == end:
                    return path
                visited.add(vertex)
                for neighbor in self.adj_list.get(vertex, []):
                    queue.append((neighbor, path + [neighbor]))
        return []
