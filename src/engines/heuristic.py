class HeuristicEngine:
    def __init__(self, schema_file="data/schema.json"):
        import json
        self.schema_file = schema_file or "data/schema.json"

        with open(self.schema_file, 'r') as f:
            self.schema = json.load(f)

    def process(self, query):
        """
        Simple keyword matching. If a table name or column name appears in the query (fuzzy match), select it.
        """
        query_words = set(query.lower().split())
        selected_tables = []
        selected_columns = []

        for table, details in self.schema.items():
            # Check if table name is somewhat in query
            table_tokens = set(table.lower().split('_'))
            if table_tokens & query_words:
                selected_tables.append(table)

            # Check columns
            for col in details['columns']:
                col_tokens = set(col.lower().split('_'))
                # Need overlap of at least 2 chars if token is short, else exact match
                for token in col_tokens:
                    if token in query_words:
                         if len(token) > 2: # Avoid matching 'id', 'is', 'a'
                            selected_columns.append(col)
                            if table not in selected_tables:
                                selected_tables.append(table)

        return {
            "tables": list(set(selected_tables)),
            "columns": list(set(selected_columns)),
            "filters": [] # Heuristic is bad at filters
        }
