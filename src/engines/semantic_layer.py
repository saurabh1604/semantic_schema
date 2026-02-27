# Semantic Layer / Metric Store Engine
import time
from .base_engine import BaseEngine

class SemanticLayerEngine(BaseEngine):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "Semantic Layer"
        self.metric_store = {
            "REVENUE": {"table": "POD_INVENTORY", "column": "MEMORY_GB", "logic": "SUM(MEMORY_GB) * $10"}, # Mock metric
            "ACTIVE_PODS": {"table": "POD_INVENTORY", "column": "POD_ID", "logic": "COUNT(POD_ID) WHERE STATUS_CD='ACTIVE'"},
            "FAILURES": {"table": "PATCH_EXECUTION_LOGS", "column": "LOG_ID", "logic": "COUNT(LOG_ID) WHERE STATUS_CD='FAILED'"},
            "PATCH_SLA": {"table": "PATCH_EXECUTION_LOGS", "column": "SLA_BREACH_FLG", "logic": "SUM(SLA_BREACH_FLG)"},
            "TICKETS": {"table": "SERVICE_REQUESTS", "column": "SR_ID", "logic": "COUNT(SR_ID)"}
        }

    def process(self, query):
        """
        Maps query terms to business metrics, then to physical tables.
        """
        start_time = time.time()
        trace = []

        # Step 1: Identify Business Metrics in Query
        query_upper = query.upper()
        found_metrics = []

        for metric, details in self.metric_store.items():
            if metric in query_upper or any(w in query_upper for w in metric.split("_")):
                found_metrics.append(metric)
                trace.append({
                    "agent": "Semantic Mapper",
                    "action": f"Found Metric: {metric}",
                    "output": f"Mapped to {details['table']}.{details['column']}"
                })

        # Step 2: Resolve Physical Layer
        tables = set()
        columns = set()
        filters = []

        for m in found_metrics:
            details = self.metric_store[m]
            tables.add(details['table'])
            columns.add(details['column'])
            if "WHERE" in details['logic']:
                filters.append(details['logic'].split("WHERE")[1].strip())

        # Fallback if no metric found -> Use LLM or Heuristic
        if not tables:
             # Just replicate Heuristic logic as fallback
             for t in self.schema:
                 if any(w in t.lower() for w in query.lower().split()):
                     tables.add(t)
                     trace.append({"agent": "Fallback", "action": "No Metric Found", "output": f"Selected {t} by keyword"})

        return {
            "tables": list(tables),
            "columns": list(columns),
            "filters": filters,
            "trace": trace,
            "execution_time": time.time() - start_time
        }
