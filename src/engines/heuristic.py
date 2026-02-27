class HeuristicEngine:
    def __init__(self, schema_file="data/schema.json", schema_dict=None, api_key=None):
        self.name = "Heuristic"
        import json
        if schema_dict:
            self.schema = schema_dict
        else:
            self.schema_file = schema_file or "data/schema.json"
            with open(self.schema_file, 'r') as f:
                self.schema = json.load(f)

    def process(self, query):
        """
        Simple keyword matching. If a table name or column name appears in the query (fuzzy match), select it.
        """
        query_lower = query.lower()
        # Create a set of tokens, but also keep the full string for substring checks
        query_words = set(query_lower.split())

        selected_tables = []
        selected_columns = []

        for table, details in self.schema.items():
            table_lower = table.lower()

            # 1. Direct Substring Match (e.g. "pod" in "POD_INVENTORY")
            # We accept a match if a significant part of the table name is in the query
            if any(part in query_lower for part in table_lower.split('_') if len(part) > 3):
                selected_tables.append(table)

            # 2. Token overlap
            table_tokens = set(table_lower.split('_'))
            if table_tokens & query_words:
                selected_tables.append(table)

            # Check columns
            for col in details['columns']:
                col_lower = col.lower()
                col_tokens = set(col_lower.split('_'))

                # Column substring match
                if any(part in query_lower for part in col_lower.split('_') if len(part) > 3):
                     selected_columns.append(col)
                     if table not in selected_tables:
                        selected_tables.append(table)

                # Token overlap
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
