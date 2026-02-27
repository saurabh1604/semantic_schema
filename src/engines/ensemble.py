# Ensemble Voting Engine
import time
from .base_engine import BaseEngine

class EnsembleVotingEngine(BaseEngine):
    def __init__(self, engines=None, **kwargs):
        super().__init__(**kwargs)
        self.name = "Ensemble Voting"
        self.sub_engines = engines or []

        # If no engines passed, we will initialize defaults later or fail gracefully
        if not self.sub_engines:
            # We assume app.py will inject them, but if not:
            try:
                from .heuristic import HeuristicEngine
                from .rag import RAGEngine
                self.sub_engines = [HeuristicEngine(**kwargs), RAGEngine(**kwargs)]
            except:
                pass

    def process(self, query):
        """
        Runs multiple engines and votes on the best tables.
        """
        start_time = time.time()
        trace = []

        votes = {}
        for engine in self.sub_engines:
            # Use getattr to safely access name or default to class name
            engine_name = getattr(engine, 'name', engine.__class__.__name__)

            if engine_name == self.name: continue # Avoid recursion

            try:
                res = engine.process(query)
                trace.append({
                    "agent": f"{engine_name}",
                    "action": "Running Sub-Engine",
                    "output": f"Found {len(res.get('tables', []))} tables"
                })

                for t in res.get('tables', []):
                    votes[t] = votes.get(t, 0) + 1
            except Exception as e:
                trace.append({"agent": f"{engine_name}", "action": "Error", "output": str(e)})

        # Majority Vote (At least 2 votes if >2 engines, else union)
        threshold = 2 if len(self.sub_engines) > 2 else 1
        final_tables = [t for t, count in votes.items() if count >= threshold]

        # Fallback if strict voting fails
        if not final_tables and votes:
            sorted_votes = sorted(votes.items(), key=lambda x: x[1], reverse=True)
            final_tables = [sorted_votes[0][0]]

        # Collect columns from winning tables
        final_cols = []
        for t in final_tables:
             if t in self.schema:
                 final_cols.extend(self.schema[t]['columns'][:5])

        return {
            "tables": final_tables,
            "columns": final_cols,
            "filters": [],
            "trace": trace,
            "execution_time": time.time() - start_time
        }
