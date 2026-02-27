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
        Adversarial Debate Execution:
        1. Proposer: "I think these tables/columns are relevant."
        2. Critic: "I reject X because it is empty. I reject Y because it has no join path."
        3. Judge: "I sustain the rejection of X. Final plan is Z."
        """
        start_time = time.time()
        trace = []

        # --- ROUND 1: PROPOSER (High Recall) ---
        proposer_start = time.time()
        proposed_tables = []

        if self.llm:
            # Proposer uses LLM to cast a wide net
            schema_keys = list(self.schema.keys())[:50]
            summary = "\n".join([f"{t}: {self.schema[t].get('description','')}" for t in schema_keys])
            proposed_tables = self.llm.extract_entities(query, summary)
        else:
            # Proposer uses fuzzy match (aggressive)
            q_lower = query.lower()
            for t in self.schema:
                if any(part in q_lower for part in t.lower().split('_')):
                    proposed_tables.append(t)

        proposed_tables = list(set(proposed_tables))
        trace.append({
            "agent": "Aegis Proposer",
            "action": "Proposed Candidate Tables (High Recall)",
            "input": query,
            "output": f"Candidates: {proposed_tables}",
            "details": "Selected based on semantic relevance."
        })

        # --- ROUND 2: CRITIC (Adversarial Validation) ---
        # The Critic checks CBO stats and Schema Constraints
        critic_start = time.time()
        approved_tables = []
        rejected_reasons = []

        for t in proposed_tables:
            if t not in self.schema:
                rejected_reasons.append(f"Rejected {t}: Does not exist in schema.")
                continue

            # Critic Check 1: Is the table empty?
            row_count = self.cbo_stats.get(t, {}).get('row_count', 100)
            if row_count == 0:
                rejected_reasons.append(f"Rejected {t}: Table is empty (0 rows).")
                continue

            # Critic Check 2: Connectivity (if multiple tables)
            # (Simplified for POC: Check if it connects to any other approved/proposed table)
            # For now, we approve if it has data.
            approved_tables.append(t)

        trace.append({
            "agent": "Aegis Critic",
            "action": "Vetoing Candidates based on Physical Stats",
            "input": f"Reviewing {len(proposed_tables)} tables",
            "output": f"Approved: {approved_tables}",
            "details": "\n".join(rejected_reasons) if rejected_reasons else "No rejections."
        })

        # --- ROUND 3: JUDGE (Synthesis) ---
        # Judge selects columns and finalize
        judge_start = time.time()
        final_columns = []

        for t in approved_tables:
            cols = self.schema[t]['columns']
            # Judge logic: "Select only non-null columns matching query keywords"
            for col in cols:
                # Check CBO
                stats = self.cbo_stats.get(t, {}).get('columns', {}).get(col, {})
                if stats.get('null_count', 0) == row_count and row_count > 0:
                    continue # Judge agrees with Critic: Skip empty col

                # Check Semantics (Simulated Judge)
                if any(w in col.lower() for w in query.lower().split()) or self.llm:
                    final_columns.append(col)

        trace.append({
            "agent": "Aegis Judge",
            "action": "Final Binding Verdict",
            "input": "Approved Tables + CBO Stats",
            "output": f"Final Plan: {len(approved_tables)} Tables, {len(final_columns)} Columns",
            "details": "Consensus reached."
        })

        return {
            "intent": "AEGIS_DEBATE",
            "tables": approved_tables,
            "columns": final_columns,
            "filters": [], # Aegis focuses on Table/Col correctness first
            "trace": trace,
            "execution_time": time.time() - start_time
        }
