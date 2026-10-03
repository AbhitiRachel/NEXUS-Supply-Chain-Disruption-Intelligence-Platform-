"""
test_sql_agent.py
--------------------
Tests the SQL agent's self-correction control flow using FAKE SQL
generators with controlled, scripted behavior -- this tests the actual
engineering contribution (detect failure -> feed back error -> retry ->
cap attempts) independently of any real LLM, which isn't available in
this environment. The real Groq-backed generator follows the exact same
interface, so this proves the loop it plugs into is correct.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.generate_sql_data import generate as generate_sql_data, DB_PATH
from src.agents.sql_agent import answer_question, get_schema_description, _is_safe_select


def setup_module(module):
    generate_sql_data()


# --- Fake generators used to script specific test scenarios ---------------

def _always_correct_generator(question, schema, error_feedback):
    return "SELECT COUNT(*) as n FROM shipments"


def _fails_once_then_succeeds_generator(question, schema, error_feedback):
    """Simulates an LLM that makes a column-name typo, then fixes it after
    seeing the error -- this is the exact behavior self-correction exists
    to handle."""
    if error_feedback is None:
        return "SELECT COUNT(*) as n FROM shipmentz"  # deliberate typo
    return "SELECT COUNT(*) as n FROM shipments"  # corrected


def _always_fails_generator(question, schema, error_feedback):
    return "SELECT COUNT(*) as n FROM this_table_does_not_exist"


def _always_unsafe_generator(question, schema, error_feedback):
    return "DROP TABLE shipments"


def _unsafe_then_safe_generator(question, schema, error_feedback):
    """Simulates a confused first attempt that tries a destructive
    query, then corrects to a safe read after being rejected."""
    if error_feedback is None:
        return "DELETE FROM shipments WHERE 1=1"
    return "SELECT COUNT(*) as n FROM shipments"


# --- Tests ------------------------------------------------------------------

def test_succeeds_on_first_try_when_generator_is_correct():
    result = answer_question("how many shipments are there?", _always_correct_generator)
    assert result.succeeded is True
    assert result.attempts_used == 1
    assert result.was_self_corrected is False
    assert result.rows[0]["n"] > 0


def test_self_correction_recovers_from_a_bad_query():
    """The core proof: the agent fails once, receives the error, and
    succeeds on retry -- this is genuine self-correction, not just
    retrying the same query."""
    result = answer_question("how many shipments are there?", _fails_once_then_succeeds_generator)
    assert result.succeeded is True
    assert result.attempts_used == 2
    assert result.was_self_corrected is True
    assert result.attempts[0].success is False
    assert "shipmentz" in result.attempts[0].sql  # confirms the bad attempt was the typo
    assert result.attempts[1].success is True
    assert result.rows[0]["n"] > 0


def test_gives_up_gracefully_after_max_attempts_exhausted():
    """When the generator can never produce working SQL, the agent must
    fail cleanly with a full attempt history -- not crash, not hang."""
    result = answer_question("impossible question", _always_fails_generator, max_attempts=3)
    assert result.succeeded is False
    assert result.attempts_used == 3
    assert all(a.success is False for a in result.attempts)
    assert result.final_sql is None


def test_destructive_query_is_rejected_not_executed():
    """A DROP TABLE must never actually run, no matter what the generator
    produces -- this is the safety guard, tested by actually trying to
    destroy data and confirming it's blocked."""
    result = answer_question("delete everything", _always_unsafe_generator, max_attempts=2)
    assert result.succeeded is False
    assert all(a.rejected_unsafe for a in result.attempts)

    # Prove the table genuinely still exists and has data after the attack attempt
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM shipments").fetchone()[0]
    conn.close()
    assert count > 0, "shipments table should be untouched"


def test_self_corrects_away_from_an_unsafe_query_toward_a_safe_one():
    """If a first attempt is destructive but the generator (after seeing
    the rejection) produces a safe query, the agent should succeed."""
    result = answer_question("show shipment count", _unsafe_then_safe_generator)
    assert result.succeeded is True
    assert result.attempts[0].rejected_unsafe is True
    assert result.attempts[1].success is True


def test_is_safe_select_rejects_non_select_statements():
    assert _is_safe_select("SELECT * FROM shipments") is True
    assert _is_safe_select("DROP TABLE shipments") is False
    assert _is_safe_select("DELETE FROM shipments") is False
    assert _is_safe_select("SELECT * FROM shipments; DROP TABLE shipments;") is False
    assert _is_safe_select("UPDATE shipments SET cost_usd=0") is False


def test_schema_description_reflects_real_database_columns():
    schema = get_schema_description(DB_PATH)
    assert "shipments" in schema
    assert "cost_usd" in schema
    assert "disruption_events" in schema
