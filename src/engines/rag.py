class RAGEngine:
    def __init__(self, schema_file="data/schema.json"):
        import json
        with open(schema_file, 'r') as f:
            self.schema = json.load(f)

        # Simulate simple "Embeddings" by just using TF-IDF logic or basic string matching
        self.embeddings = {}
        for table, details in self.schema.items():
            # Create a "document" for each table
            text = f"{table} " + " ".join(details['columns']) + " " + details['description']
            self.embeddings[table] = text.lower()

    def process(self, query):
        """
        Simulates retrieving the top-k most similar tables based on embedding similarity.
        Then asks an "LLM" (simulated) to pick columns.
        """
        query = query.lower()
        query_words = set(query.split())

        scored_tables = []
        for table, text in self.embeddings.items():
            # Jaccard similarity simulation for RAG retrieval
            doc_words = set(text.split())
            score = len(query_words & doc_words) / len(query_words | doc_words)
            scored_tables.append((score, table))

        scored_tables.sort(key=lambda x: x[0], reverse=True)
        top_k_tables = [t[1] for t in scored_tables[:3]] # Retrieve Top 3

        # LLM Simulation: "Given these tables, which columns match?"
        selected_columns = []
        for table in top_k_tables:
            for col in self.schema[table]['columns']:
                if any(word in col.lower() for word in query_words):
                    selected_columns.append(col)

        return {
            "tables": top_k_tables,
            "columns": selected_columns,
            "filters": [] # Generic RAG struggles with exact filter values without more context
        }
