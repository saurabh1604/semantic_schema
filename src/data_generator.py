import json
import random
import os

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# --- 1. Schema Generation ---
def generate_schema():
    tables = {
        "POD_INVENTORY": {
            "columns": ["POD_ID", "POD_NAME", "REGION_ID", "TENANT_TIER", "IS_TEST_POD", "CPU_CORES", "MEMORY_GB", "CREATION_DATE", "STATUS_CD"],
            "description": "Core inventory of all Fusion pods.",
            "foreign_keys": {"REGION_ID": "FND_REGIONS.REGION_ID"}
        },
        "PATCH_EXECUTION_LOGS": {
            "columns": ["LOG_ID", "POD_ID", "PATCH_ID", "START_TIME", "END_TIME", "STATUS_CD", "ERROR_CODE", "SLA_BREACH_FLG"],
            "description": "Logs of all patching activities on pods.",
            "foreign_keys": {"POD_ID": "POD_INVENTORY.POD_ID", "PATCH_ID": "PATCH_CATALOG.PATCH_ID"}
        },
        "SERVICE_REQUESTS": {
            "columns": ["SR_ID", "POD_ID", "SEVERITY_LEVEL", "SUMMARY", "DESCRIPTION", "CREATED_BY", "CREATION_DATE", "CLOSED_DATE", "RESOLUTION_CODE"],
            "description": "Support tickets raised by customers or automated systems.",
            "foreign_keys": {"POD_ID": "POD_INVENTORY.POD_ID"}
        },
        "FND_REGIONS": {
            "columns": ["REGION_ID", "REGION_NAME", "DATA_CENTER_CODE", "GEO_REGION"],
            "description": "Lookup table for geographical regions.",
            "foreign_keys": {}
        },
        "PATCH_CATALOG": {
            "columns": ["PATCH_ID", "PATCH_NAME", "VERSION_NUM", "RELEASE_DATE", "IS_CRITICAL"],
            "description": "Catalog of available patches.",
            "foreign_keys": {}
        },
        # Trap / Legacy Tables
        "POD_INVENTORY_BACKUP": {
            "columns": ["POD_ID", "POD_NAME", "BACKUP_DATE"],
            "description": "Backup of pod inventory. DO NOT USE.",
            "foreign_keys": {}
        },
        "LEGACY_PATCH_LOGS": {
            "columns": ["LOG_ID", "POD_NAME", "STATUS"],
            "description": "Deprecated patch logs from v1 system.",
            "foreign_keys": {}
        }
    }

    # Add some random junk columns to make it harder
    for table_name in tables:
        for i in range(5):
            tables[table_name]["columns"].append(f"ATTRIBUTE{i+1}")
            tables[table_name]["columns"].append(f"LEGACY_COL_{i+1}")

    return tables

# --- 2. CBO Statistics Generation ---
def generate_cbo_stats(schema):
    stats = {}
    for table, details in schema.items():
        row_count = random.randint(1000, 1000000)
        if "BACKUP" in table or "LEGACY" in table:
             row_count = random.randint(0, 500) # Trap tables are small or empty

        table_stats = {
            "row_count": row_count,
            "columns": {}
        }

        for col in details["columns"]:
            # Default stats
            null_count = random.randint(0, int(row_count * 0.1)) # 0-10% nulls usually
            distinct_values = random.randint(1, row_count)

            # Trap columns
            if "LEGACY" in col or "ATTRIBUTE" in col:
                null_count = int(row_count * random.uniform(0.9, 1.0)) # 90-100% nulls
                distinct_values = random.randint(0, 10)

            # Specific logic for important columns
            if col == "IS_TEST_POD":
                distinct_values = 2 # Y/N
            if col == "STATUS_CD":
                distinct_values = 5
            if col == "REGION_ID":
                distinct_values = 20

            table_stats["columns"][col] = {
                "null_count": null_count,
                "distinct_values": distinct_values,
                "data_distribution": "uniform" # Simplified
            }
        stats[table] = table_stats
    return stats

# --- 3. Query Log Generation (Tribal Knowledge) ---
def generate_query_logs():
    # Simulate V$SQLAREA. We store the "structure" or "ast_signature" effectively.
    # In reality, this would be raw SQL, but we'll store parsed components for the POC.
    logs = []

    # Tribal Rule 1: Always filter out test pods when querying inventory
    for _ in range(50):
        logs.append({
            "tables": ["POD_INVENTORY"],
            "columns": ["POD_ID", "POD_NAME", "STATUS_CD"],
            "filters": ["IS_TEST_POD = 'N'", "STATUS_CD = 'ACTIVE'"],
            "joins": []
        })

    # Tribal Rule 2: Join Pods and Patch Logs
    for _ in range(40):
        logs.append({
            "tables": ["POD_INVENTORY", "PATCH_EXECUTION_LOGS"],
            "columns": ["POD_NAME", "PATCH_ID", "STATUS_CD"],
            "filters": ["IS_TEST_POD = 'N'"],
            "joins": ["POD_INVENTORY.POD_ID = PATCH_EXECUTION_LOGS.POD_ID"]
        })

    # Tribal Rule 3: SLAs are only relevant for critical patches
    for _ in range(30):
        logs.append({
            "tables": ["PATCH_EXECUTION_LOGS", "PATCH_CATALOG"],
            "columns": ["PATCH_NAME", "SLA_BREACH_FLG"],
            "filters": ["IS_CRITICAL = 'Y'"],
            "joins": ["PATCH_EXECUTION_LOGS.PATCH_ID = PATCH_CATALOG.PATCH_ID"]
        })

    # Noise logs (using trap tables)
    for _ in range(5):
        logs.append({
            "tables": ["LEGACY_PATCH_LOGS"],
            "columns": ["*"],
            "filters": [],
            "joins": []
        })

    return logs

# --- 4. Ground Truth Generation ---
def generate_ground_truth():
    return [
        {
            "id": "q1",
            "query": "Show me active pods in US East region",
            "intent": "BI",
            "expected_tables": ["POD_INVENTORY", "FND_REGIONS"],
            "expected_columns": ["POD_NAME", "REGION_NAME", "STATUS_CD"],
            "required_filters": ["IS_TEST_POD = 'N'", "STATUS_CD = 'ACTIVE'", "REGION_NAME LIKE '%US East%'"]
        },
        {
            "id": "q2",
            "query": "List critical patch failures last week",
            "intent": "BI",
            "expected_tables": ["PATCH_EXECUTION_LOGS", "PATCH_CATALOG"],
            "expected_columns": ["PATCH_NAME", "STATUS_CD", "END_TIME"],
            "required_filters": ["STATUS_CD = 'FAILED'", "IS_CRITICAL = 'Y'"]
        },
        {
            "id": "q3",
            "query": "Predict pod memory usage for next upgrade",
            "intent": "ML",
            "expected_tables": ["POD_INVENTORY", "PATCH_EXECUTION_LOGS"], # Historical logs for prediction
            "expected_columns": ["MEMORY_GB", "CPU_CORES", "POD_ID", "START_TIME", "END_TIME"],
            "required_filters": ["IS_TEST_POD = 'N'"] # Implicit rule
        }
    ]

def main():
    schema = generate_schema()
    with open(os.path.join(DATA_DIR, "schema.json"), "w") as f:
        json.dump(schema, f, indent=2)

    cbo_stats = generate_cbo_stats(schema)
    with open(os.path.join(DATA_DIR, "cbo_stats.json"), "w") as f:
        json.dump(cbo_stats, f, indent=2)

    query_logs = generate_query_logs()
    with open(os.path.join(DATA_DIR, "query_logs.json"), "w") as f:
        json.dump(query_logs, f, indent=2)

    ground_truth = generate_ground_truth()
    with open(os.path.join(DATA_DIR, "ground_truth.json"), "w") as f:
        json.dump(ground_truth, f, indent=2)

    print("Mock data generated successfully in data/")

if __name__ == "__main__":
    main()
