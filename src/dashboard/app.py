"""
Streamlit dashboard for NEXUS.
Run with: streamlit run src/dashboard/app.py
Expects the FastAPI backend running at API_BASE (default http://localhost:8000).

Cannot be run/tested in this sandbox (no network access to install
streamlit) -- calls straight into the FastAPI backend's endpoints, which
themselves call the tested handlers. Test this file on your own machine
once streamlit and fastapi are installed.
"""

import os
import sqlite3
from pathlib import Path

import requests
import streamlit as st

API_BASE = os.environ.get("NEXUS_API_BASE", "http://localhost:8000")
DB_PATH = Path(__file__).parent.parent.parent / "data" / "nexus.db"

st.set_page_config(page_title="NEXUS", layout="wide")


def _auth_headers():
    return {"Authorization": f"Bearer {st.session_state['token']}"}


# --- Login screen ------------------------------------------------------------

if "token" not in st.session_state:
    st.title("🔗 NEXUS — Supply Chain Resilience Platform")
    st.caption("Sign in to continue")

    with st.form("login"):
        username = st.text_input("Username", value="analyst_demo")
        password = st.text_input("Password", type="password", value="analyst123")
        submitted = st.form_submit_button("Sign in")

    st.caption(
        "Demo accounts: viewer_demo/viewer123 (query only), "
        "analyst_demo/analyst123 (+ simulations, audit log), "
        "admin_demo/admin123 (all permissions)"
    )

    if submitted:
        try:
            resp = requests.post(f"{API_BASE}/auth/login", json={"username": username, "password": password})
            resp.raise_for_status()
            data = resp.json()
            st.session_state["token"] = data["token"]
            st.session_state["role"] = data["role"]
            st.session_state["username"] = username
            st.rerun()
        except requests.RequestException as e:
            st.error(f"Login failed: {e}")
    st.stop()


# --- Main app (authenticated) -------------------------------------------------

st.title("🔗 NEXUS — Supply Chain Resilience Platform")
st.caption(f"Signed in as {st.session_state['username']} ({st.session_state['role']})")

tabs = st.tabs(["Ask a Question", "What-If Simulation", "Executive Dashboard", "Audit Log"])

# --- Tab 1: Ask a Question -----------------------------------------------------
with tabs[0]:
    st.subheader("Ask NEXUS")
    question = st.text_input(
        "Question", placeholder="e.g. What is affected if Keelung port shuts down?"
    )
    col1, col2, col3 = st.columns(3)
    entity_type = col1.selectbox("Entity type (optional, for cascade questions)",
                                   [None, "Port", "Supplier", "Factory", "Route"])
    entity_id = col2.text_input("Entity ID (optional)", placeholder="e.g. PORT-KEELUNG")
    duration_days = col3.number_input("Duration (days, optional)", min_value=0, value=0)

    if st.button("Ask", type="primary") and question:
        with st.spinner("Routing to the right agent(s)..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/query",
                    json={
                        "question": question,
                        "entity_type": entity_type,
                        "entity_id": entity_id or None,
                        "duration_days": duration_days or None,
                    },
                    headers=_auth_headers(),
                )
                if resp.status_code == 400:
                    st.error(f"⚠️ {resp.json()['detail']}")
                else:
                    resp.raise_for_status()
                    result = resp.json()
                    st.success(result["summary"])
                    st.caption(f"Agents used: {', '.join(result['intents_used'])}")

                    if result.get("graph_result"):
                        with st.expander("Cascade details"):
                            st.json(result["graph_result"])
                    if result.get("rag_result"):
                        with st.expander("Retrieved documents"):
                            st.json(result["rag_result"])
                    if result.get("sql_result"):
                        with st.expander("Data query details"):
                            st.json(result["sql_result"])
            except requests.RequestException as e:
                st.error(f"Request failed: {e}")

# --- Tab 2: What-If Simulation --------------------------------------------------
with tabs[1]:
    st.subheader("Run a What-If Disruption Scenario")
    if st.session_state["role"] == "viewer":
        st.warning("Your role (viewer) doesn't have permission to run simulations. Sign in as analyst_demo or admin_demo.")
    else:
        col1, col2, col3 = st.columns(3)
        sim_entity_type = col1.selectbox("Entity type", ["Port", "Supplier", "Factory", "Route"])
        sim_entity_id = col2.text_input("Entity ID", placeholder="e.g. PORT-KEELUNG")
        sim_duration = col3.slider("Duration (days)", 1, 90, 7)

        if st.button("Run Simulation", type="primary") and sim_entity_id:
            with st.spinner("Tracing cascade, checking inventory buffers, estimating cost..."):
                try:
                    resp = requests.post(
                        f"{API_BASE}/whatif",
                        json={"entity_type": sim_entity_type, "entity_id": sim_entity_id, "duration_days": sim_duration},
                        headers=_auth_headers(),
                    )
                    resp.raise_for_status()
                    result = resp.json()

                    severity = result["severity"]["severity"]
                    color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")
                    st.metric("Severity", f"{color} {severity.upper()}")
                    st.metric("Estimated value at risk", f"${result['total_estimated_cost_usd']:,.2f}")

                    st.write("**Recommendation:**", result["recommendation"]["action"].replace("_", " ").title())
                    st.write(result["recommendation"]["rationale"])

                    if result["recommendation"].get("alternate_options"):
                        st.write("**Alternate supplier options:**")
                        st.table(result["recommendation"]["alternate_options"])

                    with st.expander("Buffer status by factory"):
                        st.json(result["buffer_statuses"])
                except requests.RequestException as e:
                    st.error(f"Simulation failed: {e}")

# --- Tab 3: Executive Dashboard (BA-facing KPIs) --------------------------------
with tabs[2]:
    st.subheader("Executive Summary")
    st.caption("Business-level KPIs, not agent internals -- for stakeholders who want the headline, not the mechanism.")

    try:
        conn = sqlite3.connect(DB_PATH)
        total = conn.execute("SELECT COUNT(*) FROM shipments").fetchone()[0]
        on_time = conn.execute("SELECT COUNT(*) FROM shipments WHERE status='on_time'").fetchone()[0]
        delayed = conn.execute("SELECT COUNT(*) FROM shipments WHERE status='delayed'").fetchone()[0]
        avg_delay_cost = conn.execute(
            "SELECT AVG(cost_usd) FROM shipments WHERE status='delayed'"
        ).fetchone()[0] or 0
        high_severity_events = conn.execute(
            "SELECT COUNT(*) FROM disruption_events WHERE severity='high'"
        ).fetchone()[0]
        conn.close()

        on_time_rate = (on_time / total * 100) if total else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("On-Time Delivery Rate", f"{on_time_rate:.1f}%")
        c2.metric("Delayed Shipments", delayed)
        c3.metric("Avg. Cost per Delayed Shipment", f"${avg_delay_cost:,.0f}")
        c4.metric("High-Severity Disruption Events", high_severity_events)

        st.caption(
            "These figures are computed directly from operational shipment records "
            "(synthetic data for this capstone build) -- the same records the SQL "
            "agent queries when answering natural-language questions."
        )
    except Exception as e:
        st.error(f"Could not load KPIs: {e}")

# --- Tab 4: Audit Log ------------------------------------------------------------
with tabs[3]:
    st.subheader("Tamper-Evident Audit Log")
    if st.session_state["role"] == "viewer":
        st.warning("Your role (viewer) doesn't have permission to view the audit log.")
    else:
        try:
            resp = requests.get(f"{API_BASE}/audit-log", headers=_auth_headers())
            resp.raise_for_status()
            result = resp.json()

            if result["chain_intact"]:
                st.success(f"✅ Chain intact -- {result['entry_count']} entries, no tampering detected.")
            else:
                st.error(f"⚠️ TAMPERING DETECTED: {result['integrity_issue']}")

            st.table(result["entries"])
        except requests.RequestException as e:
            st.error(f"Could not load audit log: {e}")
