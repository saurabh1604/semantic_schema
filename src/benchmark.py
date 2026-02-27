import json
import time
import csv
import os

# Import Engines
from engines.heuristic import HeuristicEngine
from engines.rag import RAGEngine
from engines.graph_rag import GraphEngine
from engines.synapse import SynapseEngine
from engines.aegis import AegisEngine
# New Engines
from engines.react import ReActEngine
from engines.hyde import HyDEEngine
from engines.ensemble import EnsembleVotingEngine
from engines.self_correction import SelfCorrectionEngine
from engines.semantic_layer import SemanticLayerEngine

DATA_DIR = "data"
RESULTS_FILE = "benchmark_results.csv"

def load_ground_truth():
    with open(os.path.join(DATA_DIR, "ground_truth.json"), 'r') as f:
        return json.load(f)

def calculate_metrics(expected, actual):
    # Precision/Recall for Tables
    exp_tables = set(expected['expected_tables'])
    act_tables = set(actual['tables'])

    tp_tables = len(exp_tables & act_tables)
    fp_tables = len(act_tables - exp_tables)
    fn_tables = len(exp_tables - act_tables)

    table_precision = tp_tables / (tp_tables + fp_tables) if (tp_tables + fp_tables) > 0 else 0
    table_recall = tp_tables / (tp_tables + fn_tables) if (tp_tables + fn_tables) > 0 else 0

    # Precision/Recall for Columns
    exp_cols = set(expected['expected_columns'])
    act_cols = set(actual['columns'])

    tp_cols = len(exp_cols & act_cols)
    fp_cols = len(act_cols - exp_cols)
    fn_cols = len(exp_cols - act_cols)

    col_precision = tp_cols / (tp_cols + fp_cols) if (tp_cols + fp_cols) > 0 else 0
    col_recall = tp_cols / (tp_cols + fn_cols) if (tp_cols + fn_cols) > 0 else 0

    # Filter Accuracy (Exact Match of Required Filters)
    exp_filters = set(expected['required_filters'])
    act_filters = set(actual['filters'])
    filter_accuracy = len(exp_filters & act_filters) / len(exp_filters) if len(exp_filters) > 0 else 1.0 # If no filters expected, 100% acc

    return {
        "table_precision": table_precision,
        "table_recall": table_recall,
        "col_precision": col_precision,
        "col_recall": col_recall,
        "filter_accuracy": filter_accuracy
    }

def run_benchmark():
    ground_truth = load_ground_truth()

    # Pre-instantiate base engines for Ensemble
    synapse = SynapseEngine()
    graph = GraphEngine()
    heuristic = HeuristicEngine()

    engines = {
        "Heuristic": heuristic,
        "Generic RAG": RAGEngine(),
        "GraphRAG": graph,
        "Project SYNAPSE": synapse,
        "Project AEGIS": AegisEngine(),
        "ReAct Agent": ReActEngine(),
        "HyDE Retrieval": HyDEEngine(),
        "Ensemble Voting": EnsembleVotingEngine(engines=[synapse, graph, heuristic]),
        "Self-Correction": SelfCorrectionEngine(),
        "Semantic Layer": SemanticLayerEngine()
    }

    results = []

    print(f"{'Engine':<20} | {'Query ID':<10} | {'Latency (ms)':<15} | {'Table Rec':<10} | {'Col Rec':<10} | {'Filter Acc':<10}")
    print("-" * 90)

    for engine_name, engine in engines.items():
        for case in ground_truth:
            start_time = time.time()
            output = engine.process(case['query'])
            latency = (time.time() - start_time) * 1000 # ms

            metrics = calculate_metrics(case, output)

            row = {
                "Engine": engine_name,
                "Query ID": case['id'],
                "Query Intent": case['intent'],
                "Latency (ms)": round(latency, 2),
                "Table Precision": round(metrics['table_precision'], 2),
                "Table Recall": round(metrics['table_recall'], 2),
                "Column Precision": round(metrics['col_precision'], 2),
                "Column Recall": round(metrics['col_recall'], 2),
                "Filter Accuracy": round(metrics['filter_accuracy'], 2),
                "Pruned Columns": output.get('pruned_columns', 0)
            }
            results.append(row)

            print(f"{engine_name:<20} | {case['id']:<10} | {row['Latency (ms)']:<15} | {row['Table Recall']:<10} | {row['Column Recall']:<10} | {row['Filter Accuracy']:<10}")

    # Write CSV
    keys = results[0].keys()
    with open(RESULTS_FILE, 'w', newline='') as f:
        dict_writer = csv.DictWriter(f, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(results)

    print(f"\nBenchmark complete. Results saved to {RESULTS_FILE}")

if __name__ == "__main__":
    run_benchmark()
