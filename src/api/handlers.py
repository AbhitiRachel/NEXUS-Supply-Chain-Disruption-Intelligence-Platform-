"""
handlers.py
-----------
The actual request-handling logic for the NEXUS API, deliberately kept
independent of FastAPI itself. FastAPI (main.py) is a thin wrapper that
extracts the auth token and request body, then calls straight into these
functions.

Why this split matters here specifically: this sandbox has no network
access to install fastapi/streamlit, so those two files cannot be
executed or tested in this environment. By keeping all real logic here
in plain functions, that logic IS fully testable right now (see
tests/test_api_handlers.py) -- only the thin routing/serialization layer
in main.py goes untested by me, and that layer is low-risk precisely
because it's thin. Run tests/test_api_handlers.py on your machine once
fastapi is installed to also exercise main.py directly if you want that
extra layer covered too.
"""
"""Handles GET /audit-log. Requires 'view_audit_log' (admin only)."""

import sqlite3
from dataclasses import asdict, is_dataclass
from pathlib import Path

from src.agents.supervisor import Supervisor
from src.agents.simulation_agent import SimulationAgent
from src.agents.recommender import Recommender
from src.security.auth import require_permission, AuthError
from src.security.prompt_guard import screen_input
from src.audit.hash_chain import AuditLog


DB_PATH = Path(__file__).parent.parent.parent / "data" / "nexus.db"


class HandlerError(Exception):
    """Raised for any handler-level failure; main.py maps this to an HTTP status."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _to_jsonable(obj):
    """Recursively converts dataclasses (and containers of them) to plain
    dicts/lists so the API layer can serialize the result directly."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    return obj


def handle_query(
    token: str,
    question: str,
    sql_generator_fn,
    audit_log: AuditLog,
    entity_type: str = None,
    entity_id: str = None,
    duration_days: int = None,
) -> dict:
    """
    Handles POST /query. Requires the 'query' permission (all roles have
    it). Screens input for prompt injection before doing anything else,
    logs the interaction, then routes through the Supervisor.
    """
    try:
        claims = require_permission(token, "query")
    except AuthError as e:
        raise HandlerError(str(e), status_code=401)

    guard_result = screen_input(question)
    if not guard_result.is_safe:
        audit_log.append(
            event_type="prompt_injection_flagged",
            actor=claims["sub"],
            details=f"Matched pattern: {guard_result.matched_pattern!r} in question: {question!r}",
        )
        raise HandlerError(
            "This question was flagged as a potential prompt injection attempt and was not processed.",
            status_code=400,
        )

    supervisor = Supervisor(sql_generator_fn=sql_generator_fn)
    result = supervisor.answer(
        question, entity_type=entity_type, entity_id=entity_id, duration_days=duration_days
    )

    audit_log.append(
        event_type="query_answered",
        actor=claims["sub"],
        details=f"Question: {question!r} | Intents: {result.intents_used} | Summary: {result.summary}",
    )

    return {
        "question": result.question,
        "intents_used": result.intents_used,
        "summary": result.summary,
        "graph_result": _to_jsonable(result.graph_result),
        "rag_result": _to_jsonable(result.rag_result),
        "sql_result": _to_jsonable(result.sql_result),
    }


def handle_whatif(
    token: str,
    entity_type: str,
    entity_id: str,
    duration_days: int,
    audit_log: AuditLog,
) -> dict:
    """
    Handles POST /whatif. Requires 'run_simulation' permission
    (analyst/admin only, not viewer) -- running a what-if scenario is a
    more privileged action than a read-only query.
    """
    try:
        claims = require_permission(token, "run_simulation")
    except AuthError as e:
        raise HandlerError(str(e), status_code=401)

    sim = SimulationAgent()
    rec = Recommender()

    whatif_result = sim.run_whatif(entity_type, entity_id, duration_days)
    recommendation = rec.recommend(whatif_result, disrupted_entity_id=entity_id)

    audit_log.append(
        event_type="whatif_simulation_run",
        actor=claims["sub"],
        details=(
            f"entity={entity_type}:{entity_id} duration={duration_days}d "
            f"severity={whatif_result.severity.severity} "
            f"recommendation={recommendation.action} "
            f"est_cost=${whatif_result.total_estimated_cost_usd:,.2f}"
        ),
    )

    return {
        "cascade": _to_jsonable(whatif_result.cascade),
        "severity": _to_jsonable(whatif_result.severity),
        "buffer_statuses": _to_jsonable(whatif_result.buffer_statuses),
        "cost_estimates": _to_jsonable(whatif_result.cost_estimates),
        "total_estimated_cost_usd": whatif_result.total_estimated_cost_usd,
        "recommendation": _to_jsonable(recommendation),
    }


def handle_get_audit_log(token: str, audit_log: AuditLog) -> dict:
    """Handles GET /audit-log. Requires 'view_audit_log' (analyst/admin only)."""
    try:
        require_permission(token, "view_audit_log")
    except AuthError as e:
        raise HandlerError(str(e), status_code=401)

    is_valid, reason = audit_log.verify_integrity()
    entries = audit_log.get_all_entries()

    return {
        "chain_intact": is_valid,
        "integrity_issue": reason,
        "entry_count": len(entries),
        "entries": [_to_jsonable(e) for e in entries],
    }


def handle_get_kpis(token: str, db_path: Path = DB_PATH) -> dict:
    """
    Handles GET /kpis. Requires the 'query' permission (all roles), the same
    as the read-only Executive Dashboard it feeds. Serving these from the API
    means the dashboard no longer needs its own copy of nexus.db, so it reads
    the same data the agents do even when deployed as a separate service.
    """
    try:
        require_permission(token, "query")
    except AuthError as e:
        raise HandlerError(str(e), status_code=401)

    conn = sqlite3.connect(db_path)
    try:
        total = conn.execute("SELECT COUNT(*) FROM shipments").fetchone()[0]
        on_time = conn.execute("SELECT COUNT(*) FROM shipments WHERE status='on_time'").fetchone()[0]
        delayed = conn.execute("SELECT COUNT(*) FROM shipments WHERE status='delayed'").fetchone()[0]
        avg_delay_cost = conn.execute(
            "SELECT AVG(cost_usd) FROM shipments WHERE status='delayed'"
        ).fetchone()[0] or 0
        high_severity_events = conn.execute(
            "SELECT COUNT(*) FROM disruption_events WHERE severity='high'"
        ).fetchone()[0]
    finally:
        conn.close()

    return {
        "total_shipments": total,
        "on_time_shipments": on_time,
        "delayed_shipments": delayed,
        "on_time_rate_pct": (on_time / total * 100) if total else 0,
        "avg_cost_per_delayed_shipment_usd": avg_delay_cost,
        "high_severity_disruption_events": high_severity_events,
    }