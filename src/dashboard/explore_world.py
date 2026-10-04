"""
explore_world.py
----------------
Orientation page for the NEXUS synthetic supply-chain world.

Everything shown here is derived at render time from data/schema.py, the
same single source of truth the graph, SQL and document generators use.
Nothing is copied or re-declared, so if schema.py changes this page
changes with it.

Read-only: no API calls, no database access, no new dependencies
(the network diagram uses st.graphviz_chart, which renders a DOT string
in the browser).
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# `streamlit run src/dashboard/app.py` puts src/dashboard on sys.path, not
# the repo root, so `data.schema` would not resolve without this.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from data.schema import (  # noqa: E402
    SUPPLIERS, PORTS, FACTORIES, PRODUCTS, ROUTES,
    SUPPLIER_TO_PORT, PORT_TO_FACTORY, FACTORY_TO_PRODUCTS, SUPPLIER_TO_FACTORIES,
)

_SUPPLIER_NAME = {sid: name for sid, name, _, _ in SUPPLIERS}
_PORT_NAME = {pid: name for pid, name, _ in PORTS}
_FACTORY_NAME = {fid: name for fid, name, _ in FACTORIES}
_PRODUCT_NAME = {pid: name for pid, name in PRODUCTS}


def _names(ids, lookup):
    return ", ".join(lookup[i] for i in ids) if ids else "-"


# --- Tables --------------------------------------------------------------------

def _suppliers_df():
    return pd.DataFrame([
        {
            "ID": sid, "Name": name, "Country": country,
            "Category": category.replace("_", " "),
            "Ships from port": _PORT_NAME[SUPPLIER_TO_PORT[sid]],
            "Feeds factories": _names(SUPPLIER_TO_FACTORIES.get(sid, []), _FACTORY_NAME),
        }
        for sid, name, country, category in SUPPLIERS
    ])


def _ports_df():
    origins = {a for a, _, _, _ in ROUTES}
    destinations = {b for _, b, _, _ in ROUTES}
    rows = []
    for pid, name, country in PORTS:
        if pid in origins and pid in destinations:
            role = "Origin and destination"
        elif pid in origins:
            role = "Origin (export)"
        elif pid in destinations:
            role = "Destination (import)"
        else:
            role = "Unconnected"
        shipping_suppliers = [s for s, p in SUPPLIER_TO_PORT.items() if p == pid]
        rows.append({
            "ID": pid, "Name": name, "Country": country, "Role": role,
            "Suppliers shipping from here": _names(shipping_suppliers, _SUPPLIER_NAME),
            "Factories supplied": _names(PORT_TO_FACTORY.get(pid, []), _FACTORY_NAME),
        })
    return pd.DataFrame(rows)


def _routes_df():
    return pd.DataFrame([
        {
            "From": _PORT_NAME[a], "To": _PORT_NAME[b],
            "Mode": mode, "Typical transit (days)": days,
        }
        for a, b, mode, days in ROUTES
    ])


def _factories_df():
    port_for_factory = {f: p for p, fl in PORT_TO_FACTORY.items() for f in fl}
    return pd.DataFrame([
        {
            "ID": fid, "Name": name, "Country": country,
            "Supplied via port": _PORT_NAME.get(port_for_factory.get(fid), "-"),
            "Fed by suppliers": _names(
                [s for s, fl in SUPPLIER_TO_FACTORIES.items() if fid in fl], _SUPPLIER_NAME),
            "Produces": _names(FACTORY_TO_PRODUCTS.get(fid, []), _PRODUCT_NAME),
        }
        for fid, name, country in FACTORIES
    ])


def _products_df():
    factory_for_product = {p: f for f, pl in FACTORY_TO_PRODUCTS.items() for p in pl}
    rows = []
    for prid, name in PRODUCTS:
        fid = factory_for_product.get(prid)
        upstream = [s for s, fl in SUPPLIER_TO_FACTORIES.items() if fid in fl] if fid else []
        rows.append({
            "ID": prid, "Name": name,
            "Made at": _FACTORY_NAME.get(fid, "-"),
            "Depends on suppliers": _names(upstream, _SUPPLIER_NAME),
        })
    return pd.DataFrame(rows)


def _dependencies_df():
    """One row per supplier: the full path it takes through the world."""
    rows = []
    for sid, name, _, _ in SUPPLIERS:
        origin = SUPPLIER_TO_PORT[sid]
        dest_ports = [b for a, b, _, _ in ROUTES if a == origin]
        fed = SUPPLIER_TO_FACTORIES.get(sid, [])
        products = [p for f in fed for p in FACTORY_TO_PRODUCTS.get(f, [])]
        rows.append({
            "Supplier": name,
            "Origin port": _PORT_NAME[origin],
            "Routes to": _names(dest_ports, _PORT_NAME),
            "Feeds factories": _names(fed, _FACTORY_NAME),
            "Products exposed": _names(products, _PRODUCT_NAME),
        })
    return pd.DataFrame(rows)


# --- Network diagram -----------------------------------------------------------

def _dot(show_feeds: bool) -> str:
    lines = [
        "digraph G {",
        '  rankdir=LR; bgcolor="transparent"; nodesep=0.25; ranksep=0.8;',
        '  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11];',
        '  edge [fontname="Helvetica", fontsize=9, color="#888888"];',
    ]
    styles = [
        (SUPPLIERS, "#dbeafe", _SUPPLIER_NAME, "Suppliers"),
        (PORTS, "#fef3c7", _PORT_NAME, "Ports"),
        (FACTORIES, "#dcfce7", _FACTORY_NAME, "Factories"),
        (PRODUCTS, "#fce7f3", _PRODUCT_NAME, "Products"),
    ]
    for items, color, names, _ in styles:
        for item in items:
            nid = item[0]
            lines.append(f'  "{nid}" [label="{names[nid]}", fillcolor="{color}"];')

    for sid, pid in SUPPLIER_TO_PORT.items():
        lines.append(f'  "{sid}" -> "{pid}";')
    for a, b, mode, days in ROUTES:
        lines.append(f'  "{a}" -> "{b}" [label="{mode}, {days}d", color="#2563eb", penwidth=1.6];')
    for pid, factories in PORT_TO_FACTORY.items():
        for fid in factories:
            lines.append(f'  "{pid}" -> "{fid}";')
    for fid, products in FACTORY_TO_PRODUCTS.items():
        for prid in products:
            lines.append(f'  "{fid}" -> "{prid}";')
    if show_feeds:
        for sid, factories in SUPPLIER_TO_FACTORIES.items():
            for fid in factories:
                lines.append(f'  "{sid}" -> "{fid}" [style=dashed, color="#c084fc"];')
    lines.append("}")
    return "\n".join(lines)


# --- Page ----------------------------------------------------------------------

def render_explore_world():
    st.subheader("Explore the NEXUS world")
    st.caption(
        "NEXUS runs on a controlled, synthetic electronics supply chain. "
        "This page shows what is in it, so the questions and simulations in the other tabs make sense. "
        "All entities are read from the same schema the rest of the platform uses."
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Suppliers", len(SUPPLIERS))
    c2.metric("Ports", len(PORTS))
    c3.metric("Routes", len(ROUTES))
    c4.metric("Factories", len(FACTORIES))
    c5.metric("Products", len(PRODUCTS))

    st.markdown(
        "**How goods flow:** Supplier → Port → Route → Destination Port → Factory → Product"
    )
    st.caption(
        "Suppliers (mostly Taiwan and Southeast Asia) ship chips and components out of a nearby port. "
        "Sea routes carry them to Yokohama, Hamburg or Rotterdam, which supply the assembly factories "
        "that build the finished products."
    )

    show_feeds = st.checkbox(
        "Also show direct supplier → factory dependencies (dashed)",
        value=False,
        help="Which factories each supplier's parts end up in. Adds lines, so it is off by default.",
    )
    st.graphviz_chart(_dot(show_feeds), use_container_width=True)
    st.caption(
        "Blue = suppliers, yellow = ports, green = factories, pink = products. "
        "Bold blue edges are shipping routes, labelled with mode and typical transit days."
    )

    t_sup, t_port, t_route, t_fac, t_prod, t_dep = st.tabs(
        ["Suppliers", "Ports", "Routes", "Factories", "Products", "Dependencies"]
    )
    with t_sup:
        st.dataframe(_suppliers_df(), hide_index=True, use_container_width=True)
    with t_port:
        st.dataframe(_ports_df(), hide_index=True, use_container_width=True)
    with t_route:
        st.dataframe(_routes_df(), hide_index=True, use_container_width=True)
    with t_fac:
        st.dataframe(_factories_df(), hide_index=True, use_container_width=True)
    with t_prod:
        st.dataframe(_products_df(), hide_index=True, use_container_width=True)
    with t_dep:
        st.caption(
            "Where each supplier's output goes, and which products are exposed if that supplier is disrupted."
        )
        st.dataframe(_dependencies_df(), hide_index=True, use_container_width=True)