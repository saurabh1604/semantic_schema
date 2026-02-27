# --- Tab 2: Live Ontology Graph ---
elif mode == "Live Ontology Graph":
    st.header("🕸️ Self-Healing Ontology Graph")
    st.markdown("Visualizing the Tables (Nodes) and Tribal Knowledge (Learned Edges) mined from `V$SQLAREA`.")

    try:
        import graphviz

        # Build Graph from Synapse Engine state
        synapse = engines["Project SYNAPSE"]

        # Create Graphviz object
        dot = graphviz.Digraph(comment='Ontology')
        dot.attr(rankdir='LR')

        # 1. Add Tables (Nodes)
        # Limit to top 20 for visibility if many
        tables_to_show = list(synapse.schema.keys())[:20]
        for table in tables_to_show:
            dot.node(table, table, shape='box', style='filled', fillcolor='lightblue')

        # 2. Add Foreign Keys (Hard Edges)
        for table in tables_to_show:
            fks = synapse.schema[table].get('foreign_keys', {})
            for col, target in fks.items():
                target_table = target.split('.')[0]
                if target_table in tables_to_show:
                    dot.edge(table, target_table, label='FK', color='black')

        # 3. Add Learned Tribal Rules (Soft Edges)
        frequent_joins = synapse.tribal_knowledge.get('frequent_joins', [])
        for join_tuple, count in frequent_joins:
            if len(join_tuple) == 2:
                t1, t2 = join_tuple
                if t1 in tables_to_show and t2 in tables_to_show:
                    dot.edge(t1, t2, label=f'Tribal ({count}x)', color='red', style='dashed', penwidth='2')

        # 4. Add Inferred Edges from CSV (if any)
        # These are stored in schema.foreign_keys by _load_from_csvs, so Step 2 covers them.
        # But we can explicitly highlight them if we track them separately.
        # For now, Step 2 is sufficient as they are treated as "schema" once inferred.

        st.graphviz_chart(dot)

        if synapse.csv_files:
            st.markdown("### 📊 Custom CSV Relationships")
            st.write("Relationships inferred from shared column names in uploaded files:")
            for table in tables_to_show:
                fks = synapse.schema[table].get('foreign_keys', {})
                for col, target in fks.items():
                    st.code(f"{table}.{col} -> {target}")

        st.markdown("### 🧠 Learned Tribal Rules")
        st.write("These rules were autonomously mined from historical query logs:")
        for join_tuple, count in frequent_joins:
            st.code(f"Frequent Join: {join_tuple} (Count: {count})")

    except ImportError:
        st.error("Graphviz not installed. Please install graphviz to view.")
    except Exception as e:
        st.error(f"Error rendering graph: {e}")
