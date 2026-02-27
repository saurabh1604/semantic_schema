# Project SYNAPSE

**Universal Situation-Aware Data Fabric POC**

This repository contains the Proof of Concept (POC) for **Project SYNAPSE**, an advanced Neuro-Symbolic architecture designed to solve the "Column Explosion" and "Tribal Knowledge" problems in massive Oracle FaaS environments.

## Quickstart

### 1. Installation
Install the required dependencies:
```bash
pip install streamlit pandas
```

### 2. Configuration
The system can run in two modes:
1.  **Simulation Mode (Default):** Uses a deterministic `MockLLM` engine. No API key required. Perfect for demos and offline testing.
2.  **Real Mode:** Connects to OpenAI's API for intent classification and entity extraction.

**To set the OpenAI API Key:**
*   **Option A (Environment Variable):**
    ```bash
    export OPENAI_API_KEY="sk-..."
    ```
*   **Option B (UI Input):** Launch the Streamlit app and enter your key in the sidebar.

### 3. Generate Mock Data
Create the realistic Oracle FaaS schema, CBO statistics, and historical query logs:
```bash
python3 src/data_generator.py
```

### 4. Run Benchmark
Compare Project SYNAPSE against Generic RAG, GraphRAG, and Heuristic baselines:
```bash
python3 src/benchmark.py
```
*Outputs results to `benchmark_results.csv`.*

### 5. Launch the App
Interact with the system via the web interface:
```bash
streamlit run src/app.py
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the detailed Executive Blueprint, including:
*   The 4-Stage Q2S2V Extraction Engine.
*   Self-Healing Ontology (Mining `V$SQLAREA`).
*   CBO Telemetry Pruning logic.
