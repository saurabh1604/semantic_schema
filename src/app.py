import streamlit as st
import json
import os
import pandas as pd
import time
import sys
import plotly.express as px

# Add src to sys.path to import modules correctly
sys.path.append(os.path.join(os.path.dirname(__file__)))

from config import config
from engines.heuristic import HeuristicEngine
from engines.rag import RAGEngine
from engines.graph_rag import GraphEngine
from engines.synapse import SynapseEngine

# --- Configuration ---
st.set_page_config(
    page_title="Project Synapse",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for "Clean/Professional" Look
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1, h2, h3 {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 300;
    }
    .stButton>button {
        width: 100%;
        border-radius: 4px;
        height: 3em;
        background-color: #007bff;
        color: white;
        border: none;
    }
    .stButton>button:hover {
        background-color: #0056b3;
        color: white;
    }
    div[data-testid="stExpander"] details summary p {
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- Initialize Engines (Cached) ---
@st.cache_resource
def load_engines(api_key=None, model="gpt-5.2", schema_file=None, cbo_file=None, logs_file=None, csv_files=None):
    synapse = SynapseEngine(model=model, schema_file=schema_file, cbo_file=cbo_file, logs_file=logs_file, csv_files=csv_files, api_key=api_key)
    shared_schema = synapse.schema
    return {
        "Synapse": synapse,
        "RAG": RAGEngine(schema_dict=shared_schema, api_key=api_key),
        "Graph": GraphEngine(schema_dict=shared_schema, api_key=api_key),
        "Heuristic": HeuristicEngine(schema_dict=shared_schema, api_key=api_key)
    }

# --- Sidebar (Minimal) ---
with st.sidebar:
    st.header("Configuration")

    # Data Upload Only
    st.subheader("Data Source")
    upload_mode = st.radio("Input Type", ["JSON Schema", "CSV Files"])

    custom_schema_path = None
    custom_cbo_path = None
    custom_logs_path = None
    csv_file_paths = []
    data_source_msg = "Default Mock Data"

    if upload_mode == "JSON Schema":
        schema_up = st.file_uploader("Schema JSON", type="json")
        cbo_up = st.file_uploader("Stats JSON", type="json")
        logs_up = st.file_uploader("Logs JSON", type="json")

        if schema_up and cbo_up and logs_up:
            custom_schema_path = "data/custom_schema.json"
            custom_cbo_path = "data/custom_cbo_stats.json"
            custom_logs_path = "data/custom_query_logs.json"

            with open(custom_schema_path, "wb") as f: f.write(schema_up.getbuffer())
            with open(custom_cbo_path, "wb") as f: f.write(cbo_up.getbuffer())
            with open(custom_logs_path, "wb") as f: f.write(logs_up.getbuffer())
            data_source_msg = "Custom JSON"

    elif upload_mode == "CSV Files":
        uploaded_csvs = st.file_uploader("Upload Tables (CSV)", type="csv", accept_multiple_files=True)
        if uploaded_csvs:
            csv_dir = "data/csv_uploads"
            os.makedirs(csv_dir, exist_ok=True)
            for uploaded_file in uploaded_csvs:
                path = os.path.join(csv_dir, uploaded_file.name)
                with open(path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                csv_file_paths.append(path)
            data_source_msg = f"{len(csv_file_paths)} CSVs Loaded"

    # Load (API Key from Config/Env) - Hidden from UI
    api_key = config.openai_api_key
    # Default model to "gpt-5.2" as requested
    engines = load_engines(api_key, "gpt-5.2", custom_schema_path, custom_cbo_path, custom_logs_path, csv_file_paths)

    if st.button("Reload System"):
        st.cache_resource.clear()
        st.rerun()

    st.divider()
    mode = st.radio("View", ["Query Playground", "Ontology Graph", "Benchmark", "Architecture"])

# --- Helper: Render Clean Output ---
def render_engine_output(engine_name, result, latency):
    with st.expander(f"{engine_name} ({latency:.0f}ms)", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Tables**")
            if result.get('tables'):
                for t in result['tables']:
                    st.text(t)
            else:
                st.caption("None selected")

        with c2:
            st.markdown("**Columns**")
            cols = result.get('columns', [])
            if cols:
                st.caption(f"{len(cols)} selected")
                with st.expander("View List"):
                    st.write(cols)
            else:
                st.caption("None selected")

        st.markdown("**Filters**")
        if result.get('filters'):
            for f in result['filters']:
                st.code(f, language="sql")
        else:
            st.caption("None applied")

def render_trace(trace):
    st.subheader("Cognitive Trace")
    for step in trace:
        with st.expander(f"{step['agent']}", expanded=True):
            st.markdown(f"**Action:** {step['action']}")
            st.text(f"Input: {step.get('input')}")
            st.markdown(f"**Output:** `{step.get('output')}`")
            if 'details' in step:
                st.caption(step['details'])

def render_execution(output):
    st.subheader("Execution Result")

    if output.get('type') == 'chart':
        if 'data' in output and output['data']:
            df = pd.DataFrame(output['data'])
            x_col = output.get('x_col')
            y_col = output.get('y_col')

            if x_col and y_col and x_col in df.columns and y_col in df.columns:
                fig = px.bar(df, x=x_col, y=y_col, template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.dataframe(df, use_container_width=True)

    elif output.get('type') == 'plan':
        for step in output.get('steps', []):
            st.markdown(f"- {step}")

    elif output.get('type') == 'prediction':
        if 'data_preview' in output:
            st.caption("Feature Store Preview")
            st.dataframe(pd.DataFrame(output['data_preview']), use_container_width=True)

# --- Views ---

# 1. Playground
if mode == "Query Playground":
    st.title("Project Synapse")
    st.caption(f"Connected to: {data_source_msg}")

    c_query, c_btn = st.columns([4, 1])
    with c_query:
        query = st.text_input("Natural Language Query", "Show me active pods in US East")
    with c_btn:
        st.write("") # Spacer
        st.write("")
        run = st.button("Run")

    if run:
        # Run ALL engines for Live Comparison
        results = {}
        for name, engine in engines.items():
            start = time.time()
            try:
                out = engine.process(query)
                lat = (time.time() - start) * 1000
                results[name] = {"out": out, "lat": lat}
            except Exception as e:
                # Log error but don't crash app
                results[name] = {"out": {"error": str(e)}, "lat": 0}

        synapse_res = results["Synapse"]

        # Layout
        c_main, c_side = st.columns([2, 1])

        with c_main:
            if 'execution_output' in synapse_res["out"]:
                render_execution(synapse_res["out"]['execution_output'])
            st.divider()
            if 'trace' in synapse_res["out"]:
                render_trace(synapse_res["out"]['trace'])

        with c_side:
            st.subheader("Engine Comparison")
            # Display Synapse First (Hero)
            render_engine_output("Synapse", synapse_res["out"], synapse_res["lat"])

            # Display Others
            for name, res in results.items():
                if name == "Synapse": continue
                render_engine_output(name, res["out"], res["lat"])

# 2. Ontology Graph
elif mode == "Ontology Graph":
    st.title("Ontology Graph")
    try:
        import graphviz
        synapse = engines["Synapse"]
        dot = graphviz.Digraph()
        dot.attr(rankdir='LR', bgcolor='transparent')
        dot.attr('node', shape='box', style='filled', fillcolor='#f0f2f6', fontname='Helvetica', color='white')
        dot.attr('edge', color='#b0b0b0')

        tables = list(synapse.schema.keys())[:20]
        for t in tables:
            dot.node(t, t)

        # FKs
        for t in tables:
            for col, target in synapse.schema[t].get('foreign_keys', {}).items():
                target_t = target.split('.')[0]
                if target_t in tables:
                    dot.edge(t, target_t)

        st.graphviz_chart(dot, use_container_width=True)
    except:
        st.error("Graphviz missing")

# 3. Benchmark
elif mode == "Benchmark":
    st.title("Performance Benchmark")
    if os.path.exists("benchmark_results.csv"):
        df = pd.read_csv("benchmark_results.csv")
        st.dataframe(df, use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            st.caption("Latency (ms)")
            st.bar_chart(df, x="Engine", y="Latency (ms)")
        with c2:
            st.caption("Recall")
            st.bar_chart(df, x="Engine", y="Table Recall")

# 4. Architecture
elif mode == "Architecture":
    st.title("System Architecture")
    st.markdown("""
    **Project Synapse** acts as a central nervous system for enterprise data interaction.

    1. **Ontology Scout:** Learns tribal knowledge from query logs.
    2. **CBO Pruner:** Reduces search space by 99% using database statistics.
    3. **Value Grounding:** Maps vague intent to precise database enums.
    4. **Execution Swarm:** Generates code for BI, ML, or Optimization tasks.
    """)
    st.code("Query -> Ontology -> CBO Pruning -> Value Grounding -> Execution", language="text")
