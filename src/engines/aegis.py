import json
import time
import random

# Import RealLLM for actual API integration
try:
    from llm_client import RealLLM
except ImportError:
    try:
        from .llm_client import RealLLM
    except ImportError:
        RealLLM = None

# Hack to allow importing config
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

class AegisEngine:
    def __init__(self, schema_file=None, cbo_file=None, logs_file=None, model="gpt-4o", csv_files=None, api_key=None):
        self.name = "Project AEGIS"
        self.schema_file = schema_file or config.schema_file
        self.cbo_file = cbo_file or config.cbo_file
        self.logs_file = logs_file or config.logs_file
        self.model = model
        self.csv_files = csv_files
        self.schema = {}
        self.cbo_stats = {}

        # Load Data (Reusing Synapse Logic for consistency)
        if self.csv_files:
            self._load_from_csvs()
        else:
            self._load_from_json()

        self.llm = None
        key_to_use = api_key or config.openai_api_key
        if key_to_use and RealLLM:
             try:
                self.llm = RealLLM(key_to_use, model=self.model)
             except:
                pass

    def _load_from_json(self):
        with open(self.schema_file, 'r') as f:
            self.schema = json.load(f)
        with open(self.cbo_file, 'r') as f:
            self.cbo_stats = json.load(f)

    def _load_from_csvs(self):
        try:
            import pandas as pd
            for path in self.csv_files:
                df = pd.read_csv(path)
                table_name = os.path.splitext(os.path.basename(path))[0].upper()

                self.schema[table_name] = {
                    "columns": list(df.columns),
                    "description": f"Imported from {os.path.basename(path)}",
                    "foreign_keys": {}
                }

                col_stats = {}
                for col in df.columns:
                    col_stats[col] = {
                        "null_count": int(df[col].isnull().sum()),
                        "distinct_values": int(df[col].nunique())
                    }
                self.cbo_stats[table_name] = {"row_count": len(df), "columns": col_stats}
        except:
            pass

    def process(self, query):
        """
        Adversarial Debate Execution (Enhanced):
        1. Proposer: Uses Semantic Density Scoring to find top candidates.
        2. Critic: Uses Graph Connectivity + CBO Stats to veto.
        3. Judge: Synthesizes final plan based on score thresholds.
        """
        start_time = time.time()
        trace = []

        # --- ROUND 1: PROPOSER (Semantic Density Scoring) ---
        proposer_start = time.time()
        scored_candidates = []
        q_lower = query.lower()
        q_words = [w for w in q_lower.split() if len(w) > 3] # Filter insignificant words

        if self.llm:
            # LLM Proposer remains same
            schema_keys = list(self.schema.keys())[:50]
            summary = "\n".join([f"{t}: {self.schema[t].get('description','')}" for t in schema_keys])
            candidates = self.llm.extract_entities(query, summary)
            for t in candidates: scored_candidates.append((10.0, t)) # Max score for LLM pick
        else:
            # Sophisticated Mock Proposer
            for t in self.schema:
                score = 0

                # 1. Table Name Matches (High Weight)
                t_parts = t.lower().split('_')
                for part in t_parts:
                    if part in q_words: score += 3.0
                    elif any(part in qw for qw in q_words): score += 1.5 # Partial

                # 2. Column Matches (Medium Weight)
                col_matches = 0
                for c in self.schema[t]['columns']:
                    c_parts = c.lower().split('_')
                    for part in c_parts:
                        if part in q_words:
                            col_matches += 1.0
                            break
                score += min(col_matches, 5) # Cap column contribution

                # 3. Description Matches (Low Weight)
                desc = self.schema[t].get('description', '').lower()
                for w in q_words:
                    if w in desc: score += 0.5

                if score > 0:
                    scored_candidates.append((score, t))

        # Sort by score and take top 5
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        proposed_tables = [x[1] for x in scored_candidates[:5]] # Top 5 candidates

        trace.append({
            "agent": "Aegis Proposer",
            "action": "Semantic Density Scoring",
            "input": f"Query terms: {q_words}",
            "output": f"Top Candidates: {proposed_tables}",
            "details": f"Scores: {[(x[1], round(x[0],1)) for x in scored_candidates[:5]]}"
        })

        # --- ROUND 2: CRITIC (Connectivity & Stats) ---
        critic_start = time.time()
        approved_tables = []
        rejected_reasons = []

        # Pre-calculate graph neighbors for connectivity check
        neighbors = {}
        for t in proposed_tables:
            neighbors[t] = set()
            if t in self.schema:
                fks = self.schema[t].get('foreign_keys', {})
                for target in fks.values():
                    neighbors[t].add(target.split('.')[0])

        # Critic Logic
        for t in proposed_tables:
            if t not in self.schema: continue

            # 1. CBO Veto: Empty Table
            row_count = self.cbo_stats.get(t, {}).get('row_count', 100)
            if row_count == 0:
                rejected_reasons.append(f"Rejected {t}: 0 rows.")
                continue

            # 2. Connectivity Veto (If we have >1 table selected)
            # If this table is isolated from other TOP candidates, it's suspicious unless it has a very high score
            is_connected = False
            if len(proposed_tables) > 1:
                my_neighbors = neighbors.get(t, set())
                # Check if connected to any *other* proposed table
                for other in proposed_tables:
                    if t == other: continue
                    other_neighbors = neighbors.get(other, set())

                    if other in my_neighbors or t in other_neighbors:
                        is_connected = True
                        break

                # Allow isolation if score is very high (e.g. direct table name match)
                my_score = next((x[0] for x in scored_candidates if x[1] == t), 0)
                if not is_connected and my_score < 4.0:
                     rejected_reasons.append(f"Rejected {t}: Isolated from other candidates (Score {my_score} < 4.0)")
                     continue

            approved_tables.append(t)

        # Self-Healing: If we rejected everything, fall back to top 1 scorer
        if not approved_tables and proposed_tables:
            fallback = proposed_tables[0]
            approved_tables.append(fallback)
            rejected_reasons.append(f"Judge Override: Restored {fallback} to avoid empty result.")

        trace.append({
            "agent": "Aegis Critic",
            "action": "Validating Connectivity & Stats",
            "input": f"Proposed: {len(proposed_tables)}",
            "output": f"Approved: {approved_tables}",
            "details": "\n".join(rejected_reasons)
        })

        # --- ROUND 3: JUDGE (Final Selection & Column Pruning) ---
        judge_start = time.time()
        final_columns = []

        for t in approved_tables:
            cols = self.schema[t]['columns']
            row_count = self.cbo_stats.get(t, {}).get('row_count', 100)

            # Strict Column Selection
            for col in cols:
                # Always include PKs/FKs for joinability
                if "ID" in col.upper() and (col.upper() == f"{t.split('_')[0]}_ID" or col.upper() in ["POD_ID", "REGION_ID", "PATCH_ID"]):
                    final_columns.append(col)
                    continue

                # Check CBO: Nulls
                stats = self.cbo_stats.get(t, {}).get('columns', {}).get(col, {})
                if stats.get('null_count', 0) == row_count and row_count > 0:
                    continue # Skip empty columns

                # Semantic Match
                col_parts = col.lower().split('_')
                if any(part in q_words for part in col_parts):
                    final_columns.append(col)

        trace.append({
            "agent": "Aegis Judge",
            "action": "Final Plan Synthesis",
            "output": f"Tables: {len(approved_tables)}, Cols: {len(final_columns)}",
            "details": "Ensured Join Keys are present."
        })

        return {
            "intent": "AEGIS_DEBATE",
            "tables": approved_tables,
            "columns": list(set(final_columns)),
            "filters": [],
            "trace": trace,
            "execution_time": time.time() - start_time
        }
