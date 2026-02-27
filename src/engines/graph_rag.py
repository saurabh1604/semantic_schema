class GraphEngine:
    def __init__(self, schema_file="data/schema.json"):
        import json
        # Handle None explicitly if passed from app.py
        self.schema_file = schema_file or "data/schema.json"

        with open(self.schema_file, 'r') as f:
            self.schema = json.load(f)

        # Build a simple graph: Bidirectional Adjacency List
        self.adj_list = {}
        for table, details in self.schema.items():
            if table not in self.adj_list:
                self.adj_list[table] = []

            for fk_col, target in details.get('foreign_keys', {}).items():
                target_table = target.split('.')[0]
                if target_table not in self.adj_list:
                    self.adj_list[target_table] = []
                self.adj_list[table].append(target_table)
                self.adj_list[target_table].append(table)

    def process(self, query):
        """
        1. Find "Seed" tables (like Keyword Search).
        2. Expand to find a connected path (Steiner Tree simulation).
        """
        import time
        start_time = time.time()

        # Step 1: Find Seeds (Fuzzy Matching Logic)
        query = query.lower()
        query_words = set(query.split())
        seed_tables = []

        for table in self.schema:
            table_tokens = set(table.lower().split('_'))
            # Check for overlap
            overlap = table_tokens & query_words
            if overlap:
                 seed_tables.append(table)

        # Step 2: Traverse Graph (Simulated Steiner Tree / Path Finding)
        if len(seed_tables) >= 2:
            path = self._find_shortest_path(seed_tables[0], seed_tables[1])
            if path:
                seed_tables.extend(path)

        # Step 3: Select columns from the connected tables
        # Very lenient selection for "Graph" approach: If the column is interesting or matches
        selected_columns = []
        for table in set(seed_tables):
            for col in self.schema[table]['columns']:
                col_tokens = set(col.lower().split('_'))
                # Need overlap of at least 2 chars if token is short, else exact match
                for token in col_tokens:
                    if token in query_words:
                         if len(token) > 2: # Avoid matching 'id', 'is', 'a'
                            selected_columns.append(col)

        return {
            "tables": list(set(seed_tables)),
            "columns": list(set(selected_columns)),
            "filters": [], # Graph alone doesn't do value grounding well
            "execution_time": time.time() - start_time
        }

    def _find_shortest_path(self, start, end):
        # Simple BFS
        queue = [(start, [start])]
        visited = set()
        while queue:
            # Check if queue is empty
            if not queue: break

            (vertex, path) = queue.pop(0)
            if vertex not in visited:
                if vertex == end:
                    return path
                visited.add(vertex)
                for neighbor in self.adj_list.get(vertex, []):
                    queue.append((neighbor, path + [neighbor]))
        return []
