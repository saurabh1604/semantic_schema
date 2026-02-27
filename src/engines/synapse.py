import json
import random
import time
import math
import re

class MockLLM:
    """
    Simulates GPT-5.2 interactions.
    In a real deployment, this would use `openai.Completion.create`
    """
    def __init__(self, schema_file="data/schema.json"):
        with open(schema_file, 'r') as f:
            self.schema = json.load(f)

    def extract_intent(self, query):
        """
        Simulates: "Given query X, classify intent as BI, ML, or OPTIMIZER"
        """
        q = query.upper()
        if "PREDICT" in q or "FORECAST" in q or "FUTURE" in q:
            return "ML"
        elif "SCHEDULE" in q or "OPTIMIZE" in q or "PLAN" in q:
            return "OPTIMIZER"
        else:
            return "BI"

    def extract_entities(self, query):
        """
        Simulates: "Extract key entities from the query that map to our known domains"
        """
        q = query.upper()
        entities = []
        if "POD" in q: entities.append("POD_INVENTORY")
        if "PATCH" in q: entities.append("PATCH_CATALOG")
        if "LOG" in q or "FAILURE" in q: entities.append("PATCH_EXECUTION_LOGS")
        if "SR" in q or "TICKET" in q: entities.append("SERVICE_REQUESTS")
        if "REGION" in q or "US" in q: entities.append("FND_REGIONS")
        return entities

class SynapseEngine:
    def __init__(self, schema_file="data/schema.json", cbo_file="data/cbo_stats.json", logs_file="data/query_logs.json"):
        with open(schema_file, 'r') as f:
            self.schema = json.load(f)
        with open(cbo_file, 'r') as f:
            self.cbo_stats = json.load(f)
        with open(logs_file, 'r') as f:
            self.logs = json.load(f)

        self.llm = MockLLM(schema_file)

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

        # 1. Intent Classification (LLM Agent)
        intent = self.llm.extract_intent(query)

        # --- Phase A: Self-Healing Ontology (Macro-Pruning & Intent) ---
        # Instead of keyword matching, we ask the "LLM" for entities
        seed_tables = set(self.llm.extract_entities(query))

        # Apply Tribal Knowledge (Implicit Joins)
        # Check if any seed tables trigger a frequent join
        # For simplicity in simulation: If PATCH_CATALOG is selected, almost always join with PATCH_EXECUTION_LOGS
        if "PATCH_CATALOG" in seed_tables and "PATCH_EXECUTION_LOGS" not in seed_tables:
             seed_tables.add("PATCH_EXECUTION_LOGS")

        applied_filters = set()
        for table in seed_tables:
            tribal_filters = self.implicit_filters.get(table, [])
            for f in tribal_filters: applied_filters.add(f)

        # Fallback if LLM fails (shouldn't happen with our simulation logic)
        if not seed_tables:
             pass # In real system, ask clarifying question

        seed_tables = list(seed_tables)

        # --- Phase B: CBO Telemetry Pruning (Meso-Pruning) ---
        # Select columns based on Utility Score U(c) = Usage + (1 - Nulls) + Entropy
        selected_columns = []
        pruned_count = 0

        for table in seed_tables:
            if table not in self.cbo_stats: continue

            table_cols = self.cbo_stats[table]['columns']
            row_count = self.cbo_stats[table]['row_count']

            for col, stats in table_cols.items():
                # Score Calculation
                # 1. Null Penalty
                if row_count > 0:
                    null_ratio = stats['null_count'] / row_count
                else:
                    null_ratio = 1.0 # Empty table

                if null_ratio > 0.9: # 90% Nulls -> Prune (Legacy/Dead columns)
                    pruned_count += 1
                    continue

                # 2. Entropy / Distinct Values
                if stats['distinct_values'] <= 1 and stats['null_count'] == 0:
                     # Constant column (Entropy = 0) -> Prune
                    pruned_count += 1
                    continue

                # 3. Usage Frequency (Simulated by simple list of "Critical" columns)
                selected_columns.append(col)

        # --- Phase C: Value Grounding (Micro-Pruning) ---
        # Map user "values" to DB "enums"
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
