# Project SYNAPSE
**The Universal Neuro-Symbolic Data Fabric for Enterprise AI**

---

## 1. Executive Summary

**Project SYNAPSE** is a next-generation "Central Nervous System" for enterprise data operations. It solves the critical bottleneck of **Column Explosion** in massive schemas (e.g., Oracle FaaS with 15,000+ tables) where traditional RAG and Text-to-SQL systems fail.

Unlike standard approaches that blindly feed schema DDLs into an LLM context window, SYNAPSE employs a **4-Stage Cognitive Funnel** to mathematically prune 99% of irrelevant metadata before the AI ever attempts to write SQL.

---

## 2. Architecture Blueprint: The 4-Stage Cognitive Funnel

### 🧠 Stage 1: Intent Classifier Agent
**Goal:** Route the query to the correct downstream execution swarm (BI, ML, or Optimization).
**Mathematical Logic:** $ \hat{y} = \text{argmax}_{c \in \{BI, ML, OPT\}} P(c | q) $

### 🕸️ Stage 2: Ontology Scout Agent (Macro-Pruning)
**Goal:** Identify the "Seed Tables" ($T_{seed}$) required to answer the query.
**Mathematical Logic:** $ T_{seed} = \text{ExtractEntities}(q) \cup \{t_j | (t_i, t_j) \in E_{tribal} \land t_i \in T_{seed}\} $

### ✂️ Stage 3: CBO Pruning Agent (Meso-Pruning)
**Goal:** Select only the active, relevant columns from the Seed Tables.
**Mathematical Logic:** $ U(c) = \alpha \cdot \text{SemanticRelevance}(q, c) + \beta \cdot (1 - \text{NullRatio}(c)) + \gamma \cdot \text{Entropy}(c) $

### 🎯 Stage 4: Value Grounding Agent (Micro-Pruning)
**Goal:** Map vague user tokens to precise database constraints.
**Mathematical Logic:** $ v^* = \text{argmin}_{v \in D_c} \text{dist}(token, v) $

---

## 3. Advanced Comparison: Cooperative vs. Adversarial Architectures

Project SYNAPSE introduces a novel comparison between two leading multi-agent paradigms:

### 🤝 Paradigm A: The Cooperative Funnel (SYNAPSE)
*   **Philosophy:** Efficiency via aggressive reduction.
*   **Flow:** Agents work sequentially to narrow the search space.
*   **Pros:** Ultra-low latency, high precision on massive schemas.
*   **Cons:** Early errors propagate downstream (if Scout misses a table, Pruner can't recover it).

### ⚔️ Paradigm B: The Adversarial Debate Swarm (AEGIS)
*   **Philosophy:** Accuracy via conflict.
*   **Flow:**
    1.  **Proposer:** Aggressively suggests candidate tables (High Recall).
    2.  **Critic:** Ruthlessly attacks suggestions using CBO stats ("Rejecting Table X because it has 0 rows").
    3.  **Judge:** Synthesizes the final plan after hearing the debate.
*   **Pros:** Extremely robust against hallucinations; self-correcting.
*   **Cons:** Higher latency due to multiple LLM turns; higher token cost.

---

## 4. Benchmark Results

| Feature | **Project SYNAPSE** | **Project AEGIS** | Generic RAG | GraphRAG |
| :--- | :--- | :--- | :--- | :--- |
| **Architecture** | **Funnel** (Filter) | **Debate** (Loop) | **Vector** (Sim) | **Graph** (BFS) |
| **Precision** | High (CBO Pruned) | **Very High** (Critic) | Low | Medium |
| **Recall** | Medium | **High** (Proposer) | Low | High |
| **Latency** | **<500ms** | ~2000ms | >2000ms | <100ms |
| **Use Case** | Real-time BI/Dashboard | Critical Financial Reporting | Simple QA | Exploration |

---

## 5. User Guide

### Quickstart
1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Configure API Key:**
    *   Create a `.env` file: `OPENAI_API_KEY=sk-...`
3.  **Run the App:**
    ```bash
    streamlit run src/app.py
    ```

### Using Custom Data
1.  Launch the App.
2.  In the Sidebar, select **"CSV Files"** under Data Source.
3.  Upload your CSVs. The system automatically infers the Schema and Graph.
