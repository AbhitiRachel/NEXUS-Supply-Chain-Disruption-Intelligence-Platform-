"""
test_data_layer.py
--------------------
Validates the synthetic data generators: internal consistency (graph
entities match SQL entities match document entities), and that
ground-truth scenarios reference real entities.
"""

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.generate_graph_data import generate as generate_graph
from data.generate_sql_data import generate as generate_sql, DB_PATH
from data.generate_documents import generate as generate_documents, OUT_DIR as DOC_DIR
from data.ground_truth_scenarios import SCENARIOS
from data.schema import all_supplier_ids, all_port_ids, all_factory_ids, all_product_ids


def setup_module(module):
    generate_graph()
    generate_sql()
    generate_documents()


def test_graph_json_has_all_entity_types():
    data = json.loads((Path(__file__).parent.parent / "data" / "graph_data.json").read_text())
    labels = {n["label"] for n in data["nodes"]}
    assert labels == {"Supplier", "Port", "Factory", "Product"}


def test_graph_node_ids_match_schema():
    data = json.loads((Path(__file__).parent.parent / "data" / "graph_data.json").read_text())
    graph_ids = {n["id"] for n in data["nodes"]}
    schema_ids = set(all_supplier_ids() + all_port_ids() + all_factory_ids() + all_product_ids())
    assert graph_ids == schema_ids


def test_every_edge_references_a_real_node():
    data = json.loads((Path(__file__).parent.parent / "data" / "graph_data.json").read_text())
    node_ids = {n["id"] for n in data["nodes"]}
    for e in data["edges"]:
        assert e["from"] in node_ids
        assert e["to"] in node_ids


def test_sql_shipments_reference_real_suppliers_and_factories():
    conn = sqlite3.connect(DB_PATH)
    supplier_ids = set(all_supplier_ids())
    factory_ids = set(all_factory_ids())
    rows = conn.execute("SELECT DISTINCT supplier_id, factory_id FROM shipments").fetchall()
    conn.close()
    assert len(rows) > 0
    for supplier_id, factory_id in rows:
        assert supplier_id in supplier_ids
        assert factory_id in factory_ids


def test_sql_disruption_events_reference_real_entities():
    conn = sqlite3.connect(DB_PATH)
    all_ids = set(all_supplier_ids() + all_port_ids() + all_factory_ids())
    rows = conn.execute("SELECT entity_id FROM disruption_events").fetchall()
    conn.close()
    assert len(rows) > 0
    for (entity_id,) in rows:
        assert entity_id in all_ids


def test_documents_index_matches_files_on_disk():
    index = json.loads((DOC_DIR / "documents_index.json").read_text())
    assert len(index) > 0
    for doc in index:
        assert (DOC_DIR / doc["filename"]).exists()


def test_documents_reference_real_entities():
    index = json.loads((DOC_DIR / "documents_index.json").read_text())
    all_ids = set(all_supplier_ids() + all_port_ids() + all_factory_ids())
    for doc in index:
        assert doc["entity_id"] in all_ids


def test_ground_truth_scenarios_reference_real_entities():
    all_ids = set(all_supplier_ids() + all_port_ids() + all_factory_ids())
    for s in SCENARIOS:
        entity = s["disrupted_entity"]
        if entity["type"] != "Route":
            assert entity["id"] in all_ids
        for sup_id in s["expected_affected_suppliers"]:
            assert sup_id in all_ids
        for fac_id in s["expected_affected_factories"]:
            assert fac_id in all_ids
        for prod_id in s["expected_affected_products"]:
            assert prod_id in all_supplier_ids() or prod_id in all_product_ids()


def test_ground_truth_scenarios_have_required_fields():
    required = {
        "id", "description", "disrupted_entity", "duration_days",
        "expected_affected_suppliers", "expected_affected_factories",
        "expected_affected_products", "expected_severity", "rationale",
    }
    for s in SCENARIOS:
        assert required.issubset(s.keys())
