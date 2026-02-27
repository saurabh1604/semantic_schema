import json
import time
from .base_engine import BaseEngine

class HyDEEngine(BaseEngine):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "HyDE Retrieval"

    def process(self, query):
        """
        Generates a hypothetical SQL query/schema, then retrieves best match.
        """
        start_time = time.time()
        trace = []

        hypothetical_query = ""

        if self.llm:
            prompt = f"""
            You are a HyDE (Hypothetical Document Embeddings) generator.
            Given the user question: "{query}", generate a hypothetical SQL query that would answer this question.
            Do not worry about the exact schema. Just hallucinate a plausible SQL query using standard naming conventions.
            """
            hypothetical_query = self.llm._call_gpt(prompt, "Generate SQL")
            trace.append({
                "agent": "HyDE Generator",
                "action": "Hallucinating SQL",
                "output": hypothetical_query
            })
        else:
            hypothetical_query = f"SELECT * FROM {query.replace(' ', '_').upper()} WHERE status = 'ACTIVE'"
            trace.append({
                "agent": "HyDE Generator (Mock)",
                "action": "Hallucinating SQL",
                "output": hypothetical_query
            })

        # Match Hypothetical Tokens to Real Schema
        hypothetical_tokens = set(hypothetical_query.upper().replace("_", " ").split())

        selected_tables = []
        for table, details in self.schema.items():
            table_tokens = set(table.replace("_", " ").split())
            col_tokens = set()
            for c in details['columns']:
                col_tokens.update(c.replace("_", " ").split())

            # Simple Jaccard
            score = len(hypothetical_tokens & (table_tokens | col_tokens))
            if score > 0:
                selected_tables.append((score, table))

        selected_tables.sort(key=lambda x: x[0], reverse=True)
        top_tables = [t[1] for t in selected_tables[:3]]

        final_cols = []
        for t in top_tables:
            final_cols.extend(self.schema[t]['columns'][:5])

        return {
            "tables": top_tables,
            "columns": final_cols,
            "filters": [],
            "trace": trace,
            "execution_time": time.time() - start_time
        }
