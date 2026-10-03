"""
generate_graph_data.py
-----------------------
Builds the supply chain knowledge graph from schema.py and outputs it two
ways:
  1. graph_data.cypher -- run this directly against a Neo4j instance
  2. graph_data.json -- the same graph as plain nodes/edges

Node types: Supplier, Port, Factory, Product
Edge types:
  (Supplier)-[:SHIPS_FROM]->(Port)
  (Port)-[:ROUTE_TO {mode, days}]->(Port)
  (Port)-[:SUPPLIES]->(Factory)
  (Supplier)-[:FEEDS]->(Factory)
  (Factory)-[:PRODUCES]->(Product)
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.schema import (
    SUPPLIERS, PORTS, FACTORIES, PRODUCTS, ROUTES,
    SUPPLIER_TO_PORT, PORT_TO_FACTORY, FACTORY_TO_PRODUCTS, SUPPLIER_TO_FACTORIES,
)

OUT_DIR = Path(__file__).parent


def build_graph():
    nodes = []
    edges = []

    for sid, name, country, category in SUPPLIERS:
        nodes.append({"id": sid, "label": "Supplier", "name": name,
                       "country": country, "category": category})

    for pid, name, country in PORTS:
        nodes.append({"id": pid, "label": "Port", "name": name, "country": country})

    for fid, name, country in FACTORIES:
        nodes.append({"id": fid, "label": "Factory", "name": name, "country": country})

    for prid, name in PRODUCTS:
        nodes.append({"id": prid, "label": "Product", "name": name})

    for sid, pid in SUPPLIER_TO_PORT.items():
        edges.append({"from": sid, "to": pid, "type": "SHIPS_FROM"})

    for from_port, to_port, mode, days in ROUTES:
        edges.append({"from": from_port, "to": to_port, "type": "ROUTE_TO",
                       "mode": mode, "days": days})

    for pid, factory_list in PORT_TO_FACTORY.items():
        for fid in factory_list:
            edges.append({"from": pid, "to": fid, "type": "SUPPLIES"})

    for sid, factory_list in SUPPLIER_TO_FACTORIES.items():
        for fid in factory_list:
            edges.append({"from": sid, "to": fid, "type": "FEEDS"})

    for fid, product_list in FACTORY_TO_PRODUCTS.items():
        for prid in product_list:
            edges.append({"from": fid, "to": prid, "type": "PRODUCES"})

    return nodes, edges


def to_cypher(nodes, edges) -> str:
    lines = ["// NEXUS supply chain graph -- generated, do not hand-edit", ""]

    lines.append("// Constraints (run once)")
    for label in ["Supplier", "Port", "Factory", "Product"]:
        lines.append(
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE;"
        )
    lines.append("")

    lines.append("// Nodes")
    for n in nodes:
        props = {k: v for k, v in n.items() if k not in ("id", "label")}
        prop_str = ", ".join(f"{k}: {json.dumps(v)}" for k, v in props.items())
        lines.append(f'MERGE (:{n["label"]} {{id: {json.dumps(n["id"])}, {prop_str}}});')
    lines.append("")

    lines.append("// Edges")
    for e in edges:
        extra = {k: v for k, v in e.items() if k not in ("from", "to", "type")}
        extra_str = ""
        if extra:
            extra_str = " {" + ", ".join(f"{k}: {json.dumps(v)}" for k, v in extra.items()) + "}"
        lines.append(
            f'MATCH (a {{id: {json.dumps(e["from"])}}}), (b {{id: {json.dumps(e["to"])}}}) '
            f'MERGE (a)-[:{e["type"]}{extra_str}]->(b);'
        )

    return "\n".join(lines)


def generate():
    nodes, edges = build_graph()

    (OUT_DIR / "graph_data.json").write_text(
        json.dumps({"nodes": nodes, "edges": edges}, indent=2)
    )
    (OUT_DIR / "graph_data.cypher").write_text(to_cypher(nodes, edges))

    print(f"Generated {len(nodes)} nodes, {len(edges)} edges")
    print(f"  -> {OUT_DIR / 'graph_data.json'}")
    print(f"  -> {OUT_DIR / 'graph_data.cypher'}")


if __name__ == "__main__":
    generate()
