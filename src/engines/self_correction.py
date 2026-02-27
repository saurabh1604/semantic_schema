# Self-Correction Engine
import time
from .base_engine import BaseEngine

class SelfCorrectionEngine(BaseEngine):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "Self-Correction"

    def process(self, query):
        """
        Initial selection -> Validation (FK check) -> Refinement.
        """
        start_time = time.time()
        trace = []

        # Phase 1: Fast Initial Selection (Simulated Heuristic)
        initial_tables = []
        for t in self.schema:
            if any(w in t.lower() for w in query.lower().split()):
                initial_tables.append(t)

        if not initial_tables:
            initial_tables = ["POD_INVENTORY"] # Default

        trace.append({
            "agent": "Fast Scout",
            "action": "Initial Guess",
            "output": f"Tables: {initial_tables}"
        })

        # Phase 2: Self-Correction (LLM based if available)
        final_tables = list(initial_tables)

        if self.llm:
            prompt = f"""
            You are a rigorous DB Auditor. The initial agent selected these tables: {initial_tables} for the query: "{query}".

            Identify any missing tables required for JOINs or context.
            Identify any tables that are completely irrelevant and should be removed.

            Schema Context:
            {", ".join(self.schema.keys())}

            Return a corrected JSON list of tables.
            """

            correction = self.llm._call_gpt(prompt, "Audit Selection")
            if correction:
                import json
                try:
                    import re
                    match = re.search(r"\[.*\]", correction, re.DOTALL)
                    if match:
                        final_tables = json.loads(match.group(0))
                        trace.append({
                            "agent": "Auditor LLM",
                            "action": "Correction applied",
                            "output": f"Final: {final_tables}"
                        })
                except:
                    trace.append({"agent": "Auditor LLM", "action": "Failed to parse JSON", "output": correction})

        else:
            # Mock Correction Logic: Check FKs
            added = []
            for t in initial_tables:
                fks = self.schema[t].get('foreign_keys', {})
                for col, target in fks.items():
                    target_table = target.split('.')[0]
                    if target_table not in final_tables:
                        # Only add if it seems relevant? Naive correction adds all parents
                        added.append(target_table)

            final_tables.extend(added)
            if added:
                trace.append({
                    "agent": "Constraint Checker",
                    "action": "Added Missing Parents",
                    "output": f"Added: {added}"
                })

        final_cols = []
        for t in final_tables:
            if t in self.schema:
                final_cols.extend(self.schema[t]['columns'][:5])

        return {
            "tables": list(set(final_tables)),
            "columns": final_cols,
            "filters": [],
            "trace": trace,
            "execution_time": time.time() - start_time
        }
