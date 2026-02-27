import os
import json
import time

class RealLLM:
    def __init__(self, api_key, model="gpt-4o"):
        self.api_key = api_key
        self.model = model

        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
            self.available = True
        except ImportError:
            print("Warning: 'openai' library not installed. Using Mock Mode.")
            self.available = False
        except Exception as e:
            print(f"Error initializing OpenAI: {e}")
            self.available = False

    def _call_gpt(self, system_prompt, user_prompt):
        if not self.available:
            print("OpenAI client not available.")
            return None

        try:
            print(f"[DEBUG] Calling {self.model}...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API Error: {e}")
            return None

    def extract_intent(self, query):
        """
        Classify intent as BI, ML, or OPTIMIZER.
        """
        if not self.available:
            return "BI" # Fallback

        system = """You are an AI classifier for an enterprise Oracle system.
        Classify the user query into exactly one of these categories:
        - BI (Business Intelligence, Reporting, dashboards)
        - ML (Machine Learning, predictions, forecasting, root cause analysis)
        - OPTIMIZER (Scheduling, planning, constraints, migration)

        Output ONLY the category name."""

        result = self._call_gpt(system, query)
        print(f"[DEBUG] Intent Extraction Result: {result}")
        return result.strip() if result else "BI"

    def extract_entities(self, query, schema_summary):
        """
        Extract key tables/entities from the query based on the schema summary.
        """
        if not self.available:
            return []

        system = f"""You are a Database Expert. Given the following schema summary:
        {schema_summary}

        Identify the most relevant tables for the user's query.
        Return a JSON list of table names ONLY. Example: ["TABLE_A", "TABLE_B"]"""

        result = self._call_gpt(system, query)
        print(f"[DEBUG] Entity Extraction Result: {result}")

        if not result:
            return []

        try:
            # Clean up potential markdown formatting
            cleaned_result = result.replace("```json", "").replace("```", "").strip()
            # If the LLM returned a plain string list or comma separated, try to handle it
            if not cleaned_result.startswith("["):
                 # Fallback parsing attempt
                 if "," in cleaned_result:
                    return [x.strip() for x in cleaned_result.split(",")]
                 return [cleaned_result]
            return json.loads(cleaned_result)
        except Exception as e:
            print(f"[ERROR] Failed to parse entities JSON: {e}")
            return []

    def select_columns(self, query, table_name, columns):
        """
        Select relevant columns from a specific table.
        """
        if not self.available:
            return columns[:5] # Fallback

        system = f"""You are a SQL Expert. Given the table '{table_name}' with columns: {columns}

        Select the columns relevant to the user's query.
        Return a JSON list of column names ONLY."""

        result = self._call_gpt(system, query)
        try:
            cleaned_result = result.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned_result)
        except:
            return []
