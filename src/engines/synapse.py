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
    # If path issue
    try:
        from .llm_client import RealLLM
    except ImportError:
        RealLLM = None

# Hack to allow importing config from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from config import config
except ImportError:
    # Fallback if run directly or path issue
    class Config:
        def __init__(self):
            self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
            self.data_dir = "data"
            self.schema_file = "data/schema.json"
            self.cbo_file = "data/cbo_stats.json"
            self.logs_file = "data/query_logs.json"
    config = Config()

class MockLLM:
    """
    Mock LLM for Simulation Mode.
    Deterministically simulates 'gpt-5.2' behavior.
    """
    def __init__(self, schema_file="data/schema.json"):
        with open(schema_file, 'r') as f:
            self.schema = json.load(f)

    def extract_intent(self, query):
        q = query.upper()
        if "PREDICT" in q or "FORECAST" in q or "FUTURE" in q: return "ML"
        elif "SCHEDULE" in q or "OPTIMIZE" in q or "PLAN" in q: return "OPTIMIZER"
        else: return "BI"

    def extract_entities(self, query):
        q = query.upper()
        entities = []
        if "POD" in q: entities.append("POD_INVENTORY")
        if "PATCH" in q: entities.append("PATCH_CATALOG")
        if "LOG" in q or "FAILURE" in q: entities.append("PATCH_EXECUTION_LOGS")
        if "SR" in q or "TICKET" in q: entities.append("SERVICE_REQUESTS")
        if "REGION" in q or "US" in q: entities.append("FND_REGIONS")
        return entities

class SynapseEngine:
    def __init__(self, schema_file=None, cbo_file=None, logs_file=None):
        self.schema_file = schema_file or config.schema_file
        self.cbo_file = cbo_file or config.cbo_file
        self.logs_file = logs_file or config.logs_file

        with open(self.schema_file, 'r') as f:
            self.schema = json.load(f)
        with open(self.cbo_file, 'r') as f:
            self.cbo_stats = json.load(f)
        with open(self.logs_file, 'r') as f:
            self.logs = json.load(f)

        self.mock_llm = MockLLM(self.schema_file)
        self.real_llm = None
        if config.openai_api_key and RealLLM:
             try:
                self.real_llm = RealLLM(config.openai_api_key)
             except Exception as e:
                print(f"Error initializing RealLLM: {e}")

        # Build Self-Healing Ontology (Mining Query Logs for Tribal Knowledge)
        self.tribal_knowledge = {}
        self.implicit_filters = {}
        self._learn_tribal_knowledge()

    def _learn_tribal_knowledge(self):
        """
        Phase A: Self-Healing Ontology - Learning from Historical Queries (V$SQLAREA)
        """
        table_pairs = {}
        filters_map = {}

        for log in self.logs:
            # Count table co-occurrences
            tables = tuple(sorted(log['tables']))
            if tables not in table_pairs:
                table_pairs[tables] = 0
            table_pairs[tables] += 1

            # Learn implicit filters for tables
            for table in log['tables']:
                if table not in filters_map:
                    filters_map[table] = []
                filters_map[table].extend(log['filters'])

        # Store "Top Tribal Rules"
        self.tribal_knowledge['frequent_joins'] = sorted(table_pairs.items(), key=lambda x: x[1], reverse=True)[:5]

        for table, filters in filters_map.items():
            if not filters: continue
            from collections import Counter
            counts = Counter(filters)
            total = len(filters)
            # Threshold: If filter appears > 50% of time for this table, it is TRIBAL KNOWLEDGE
            top_filters = [f for f, c in counts.items() if c/total > 0.5]
            self.implicit_filters[table] = list(set(top_filters))

    def process(self, query):
        """
        Project SYNAPSE: The 4-Stage Funnel
        """
        start_time = time.time()

        # 1. Intent Classification
        if self.real_llm:
            intent = self.real_llm.extract_intent(query)
        else:
            intent = self.mock_llm.extract_intent(query)

        # --- Phase A: Self-Healing Ontology (Macro-Pruning & Intent) ---
        if self.real_llm:
            # Summarize Schema for prompt efficiency
            schema_summary = "\n".join([f"{t}: {d['description']}" for t, d in self.schema.items()])
            extracted_tables = self.real_llm.extract_entities(query, schema_summary)
            seed_tables = set(extracted_tables)
        else:
            seed_tables = set(self.mock_llm.extract_entities(query))

        # Apply Tribal Knowledge (Implicit Joins)
        if "PATCH_CATALOG" in seed_tables and "PATCH_EXECUTION_LOGS" not in seed_tables:
             seed_tables.add("PATCH_EXECUTION_LOGS")

        applied_filters = set()
        for table in seed_tables:
            tribal_filters = self.implicit_filters.get(table, [])
            for f in tribal_filters: applied_filters.add(f)

        # Fallback if LLM fails (empty seed)
        if not seed_tables:
             pass

        seed_tables = list(seed_tables)

        # --- Phase B: CBO Telemetry Pruning (Meso-Pruning) ---
        selected_columns = []
        pruned_count = 0

        for table in seed_tables:
            if table not in self.cbo_stats: continue

            table_cols = self.cbo_stats[table]['columns']
            row_count = self.cbo_stats[table]['row_count']

            # CBO Pruning Logic
            for col, stats in table_cols.items():
                if row_count > 0:
                    null_ratio = stats['null_count'] / row_count
                else:
                    null_ratio = 1.0

                if null_ratio > 0.9:
                    pruned_count += 1
                    continue

                if stats['distinct_values'] <= 1 and stats['null_count'] == 0:
                    pruned_count += 1
                    continue

                selected_columns.append(col)

        # --- Phase C: Value Grounding (Micro-Pruning) ---
        query_upper = query.upper()
        if "US EAST" in query_upper and "FND_REGIONS" in seed_tables:
             applied_filters.add("REGION_NAME LIKE '%US East%'")
        if "CRITICAL" in query_upper and "PATCH_CATALOG" in seed_tables:
            applied_filters.add("IS_CRITICAL = 'Y'")

        return {
            "intent": intent,
            "tables": seed_tables,
            "columns": list(set(selected_columns)),
            "filters": list(applied_filters),
            "pruned_columns": pruned_count,
            "execution_time": time.time() - start_time
        }
