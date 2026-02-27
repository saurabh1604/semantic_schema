# Semantic Layer / Metric Store Engine
import time
from .base_engine import BaseEngine

class SemanticLayerEngine(BaseEngine):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "Semantic Layer"
        self.metric_store = {
            # BI Metrics
            "REVENUE": {"table": "POD_INVENTORY", "column": "MEMORY_GB", "logic": "SUM(MEMORY_GB) * $10"},
            "ACTIVE_PODS": {"table": "POD_INVENTORY", "column": "POD_NAME", "logic": "COUNT(POD_ID) WHERE STATUS_CD='ACTIVE'"},
            "PODS": {"table": "POD_INVENTORY", "column": "POD_NAME", "logic": "LIST(POD_NAME)"},
            "REGIONS": {"table": "FND_REGIONS", "column": "REGION_NAME", "logic": "LIST(REGION_NAME)"},
            "US_EAST": {"table": "FND_REGIONS", "column": "REGION_NAME", "logic": "REGION_NAME LIKE '%US East%'"},

            # Patch Metrics
            "FAILURES": {"table": "PATCH_EXECUTION_LOGS", "column": "LOG_ID", "logic": "COUNT(LOG_ID) WHERE STATUS_CD='FAILED'"},
            "PATCHES": {"table": "PATCH_CATALOG", "column": "PATCH_NAME", "logic": "LIST(PATCH_NAME)"},
            "CRITICAL": {"table": "PATCH_CATALOG", "column": "IS_CRITICAL", "logic": "IS_CRITICAL='Y'"},
            "PATCH_SLA": {"table": "PATCH_EXECUTION_LOGS", "column": "SLA_BREACH_FLG", "logic": "SUM(SLA_BREACH_FLG)"},
            "UPGRADE": {"table": "PATCH_EXECUTION_LOGS", "column": "PATCH_ID", "logic": "JOIN(PATCH_EXECUTION_LOGS)"},

            # ML Features
            "MEMORY": {"table": "POD_INVENTORY", "column": "MEMORY_GB", "logic": "AVG(MEMORY_GB)"},
            "CPU": {"table": "POD_INVENTORY", "column": "CPU_CORES", "logic": "AVG(CPU_CORES)"},
            "PREDICT": {"table": "POD_INVENTORY", "column": "POD_ID", "logic": "ML_MODEL_TARGET"},

            # Support
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

        # Split query into words to match partial metrics (e.g. "PODS" in "ACTIVE PODS")
        q_words = query_upper.split()

        for metric, details in self.metric_store.items():
            # Check for exact metric match first
            if metric in query_upper:
                 found_metrics.append(metric)
                 trace.append({"agent": "Semantic Mapper", "action": f"Found Metric: {metric}", "output": f"Mapped to {details['table']}"})

            # Check for partial match (e.g., "FAILURES" matches "FAILURE")
            elif any(w in query_upper for w in metric.split('_')):
                # Be careful not to over-match short words like "US"
                if len(metric) > 3:
                     # Check if it's already added
                     if metric not in found_metrics:
                         found_metrics.append(metric)
                         trace.append({"agent": "Semantic Mapper", "action": f"Found Metric: {metric} (Partial)", "output": f"Mapped to {details['table']}"})

        # Special Case: "US East" -> US_EAST metric
        if "US EAST" in query_upper and "US_EAST" not in found_metrics:
            found_metrics.append("US_EAST")

        # Step 2: Resolve Physical Layer
        tables = set()
        columns = set()
        filters = []

        for m in found_metrics:
            details = self.metric_store[m]
            tables.add(details['table'])

            # Logic: If metric implies a JOIN, add the join table too (naive)
            if "JOIN" in details['logic']:
                 # "UPGRADE" maps to PATCH_EXECUTION_LOGS, but if we also have "PODS", we are good.
                 pass

            # Add primary column
            columns.add(details['column'])

            # Add implicit columns for context based on query words
            t = details['table']
            if "STATUS" in query_upper and "STATUS_CD" in self.schema[t]['columns']:
                columns.add("STATUS_CD")
            if "NAME" in query_upper:
                # Try to find NAME column in table
                for c in self.schema[t]['columns']:
                    if "NAME" in c: columns.add(c)

            # Add columns for filters
            if "WHERE" in details['logic']:
                filters.append(details['logic'].split("WHERE")[1].strip())
            elif "LIKE" in details['logic'] or "=" in details['logic']:
                 filters.append(details['logic'])

        # Fallback if no metric found -> Use Heuristic
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
