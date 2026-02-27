# ReAct Agent implementation for schema selection
from .base_engine import BaseEngine
import json
import time
import re

class ReActEngine(BaseEngine):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "ReAct Agent"

    def process(self, query):
        """
        Implements a Reasoning + Acting loop.
        Thought -> Action -> Observation
        """
        start_time = time.time()
        trace = []

        # Initial context
        schema_summary = "\n".join([f"{t}: {self.schema[t].get('description','')}" for t in self.schema.keys()][:50])

        # Simple ReAct Loop (Mock for speed if no LLM)
        if not self.llm:
            trace.append({"agent": "ReAct", "action": "Thought", "output": "I need to find tables related to the query."})
            trace.append({"agent": "ReAct", "action": "Action", "output": "Search Schema for keywords"})
            trace.append({"agent": "ReAct", "action": "Observation", "output": "Found potential matches."})

            # Simulated Trace for "US East" -> FND_REGIONS
            found_tables = []
            q_words = query.lower().split()

            # Step 1: Identify Nouns
            nouns = [w for w in q_words if len(w) > 3]

            for noun in nouns:
                for t in self.schema:
                    # Direct Match
                    if noun in t.lower():
                        found_tables.append(t)
                        trace.append({"agent": "ReAct", "action": "Thought", "output": f"Found table {t} matching '{noun}'"})

                    # Column Match (e.g. "Region" -> "REGION_NAME")
                    for c in self.schema[t]['columns']:
                        if noun in c.lower() and t not in found_tables:
                             found_tables.append(t)
                             trace.append({"agent": "ReAct", "action": "Thought", "output": f"Found column {c} matching '{noun}' in {t}"})

            # Step 2: Resolve Joins (Simple)
            if "POD_INVENTORY" in found_tables and "US" in query.upper():
                if "FND_REGIONS" not in found_tables:
                    found_tables.append("FND_REGIONS")
                    trace.append({"agent": "ReAct", "action": "Thought", "output": "Adding FND_REGIONS for location context"})

            found_tables = list(set(found_tables))

            # Step 3: Select Columns
            final_cols = []
            for t in found_tables:
                for c in self.schema[t]['columns']:
                     if any(w in c.lower() for w in q_words if len(w) > 3):
                         final_cols.append(c)
                     elif "ID" in c and c.startswith(t.split('_')[0]):
                         final_cols.append(c)
                     elif "NAME" in c or "STATUS" in c:
                         final_cols.append(c)

            return {
                "tables": found_tables,
                "columns": final_cols,
                "filters": [],
                "trace": trace,
                "execution_time": time.time() - start_time
            }

        # Real LLM ReAct Simulation
        max_steps = 3
        history = f"Schema Summary:\n{schema_summary}\n\nUser Query: {query}\n"

        tables_found = []

        for i in range(max_steps):
            prompt = f"""You are a ReAct agent. Solve the user query by finding the relevant tables.

            Tools available:
            1. lookup_table_columns(table_name): Returns columns for a table.
            2. search_tables(keyword): Returns tables matching a keyword.
            3. finish(tables=[]): Returns the final answer.

            Format:
            Thought: [Your reasoning]
            Action: [Tool Name]
            Action Input: [Input]

            History:
            {history}
            """

            response = self.llm._call_gpt(prompt, "Next Step")
            if not response: break

            trace.append({
                "agent": "ReAct Agent",
                "action": f"Step {i+1}",
                "output": response
            })

            history += f"\nAgent: {response}\n"

            if "finish" in response.lower():
                # Extract tables from response (naive parsing)
                import re
                matches = re.findall(r"['\"]([A-Z_]+)['\"]", response)
                tables_found.extend([m for m in matches if m in self.schema])
                break

            elif "lookup_table_columns" in response.lower():
                # Extract table name
                import re
                match = re.search(r"lookup_table_columns\(['\"]?([A-Z_]+)['\"]?\)", response)
                if match:
                    t = match.group(1)
                    if t in self.schema:
                        obs = f"Columns for {t}: {list(self.schema[t]['columns'])}"
                    else:
                        obs = f"Table {t} not found."
                else:
                    obs = "Invalid tool usage."

                history += f"\nObservation: {obs}\n"
                trace.append({"agent": "Environment", "action": "Observation", "output": obs})

            elif "search_tables" in response.lower():
                # Extract keyword
                import re
                match = re.search(r"search_tables\(['\"]?(\w+)['\"]?\)", response)
                if match:
                    kw = match.group(1).upper()
                    found = [t for t in self.schema if kw in t]
                    obs = f"Found tables: {found}"
                else:
                    obs = "Invalid tool usage."

                history += f"\nObservation: {obs}\n"
                trace.append({"agent": "Environment", "action": "Observation", "output": obs})

        tables_found = list(set(tables_found))

        # Select columns for found tables (Standard fallback)
        final_cols = []
        for t in tables_found:
             final_cols.extend(self.schema[t]['columns'][:5])

        return {
            "tables": tables_found,
            "columns": final_cols,
            "filters": [],
            "trace": trace,
            "execution_time": time.time() - start_time
        }
