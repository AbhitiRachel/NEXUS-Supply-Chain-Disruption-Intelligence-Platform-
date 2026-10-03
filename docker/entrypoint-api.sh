#!/bin/sh
set -e

# Generate data on first boot if it isn't already present (e.g. a fresh
# container, or a mounted empty volume) -- makes the image self-sufficient
# without needing to bake a specific dataset snapshot into it.
if [ ! -f "data/nexus.db" ]; then
    echo "No existing data found -- generating synthetic dataset..."
    python data/generate_graph_data.py
    python data/generate_sql_data.py
    python data/generate_documents.py
fi

exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000
