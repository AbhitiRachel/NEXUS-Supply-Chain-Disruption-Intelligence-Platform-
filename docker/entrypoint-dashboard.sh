#!/bin/sh
set -e

if [ ! -f "data/nexus.db" ]; then
    echo "No existing data found -- generating synthetic dataset..."
    python data/generate_graph_data.py
    python data/generate_sql_data.py
    python data/generate_documents.py
fi

exec streamlit run src/dashboard/app.py --server.address=0.0.0.0 --server.port=8501
