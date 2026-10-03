"""
test_hash_chain.py
---------------------
Tests the audit log's core promise: tampering with any past record is
detectable. The key test doesn't just check the API -- it directly
edits a row in the database with raw SQL (bypassing the AuditLog class
entirely, simulating an attacker with direct database access) and
confirms verify_integrity() catches it.
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.audit.hash_chain import AuditLog, GENESIS_HASH

TEST_DB = Path(__file__).parent / "_test_audit.db"


def setup_function(function):
    TEST_DB.unlink(missing_ok=True)


def teardown_function(function):
    TEST_DB.unlink(missing_ok=True)


def test_first_entry_chains_from_genesis_hash():
    log = AuditLog(db_path=TEST_DB)
    entry = log.append("disruption_logged", "analyst_1", "Port strike at Keelung")
    assert entry.prev_hash == GENESIS_HASH


def test_second_entry_chains_from_first_entrys_hash():
    log = AuditLog(db_path=TEST_DB)
    first = log.append("disruption_logged", "analyst_1", "Port strike at Keelung")
    second = log.append("recommendation_issued", "system", "Shift orders to Murata")
    assert second.prev_hash == first.entry_hash


def test_untampered_chain_verifies_as_intact():
    log = AuditLog(db_path=TEST_DB)
    log.append("disruption_logged", "analyst_1", "Port strike at Keelung")
    log.append("recommendation_issued", "system", "Shift orders to Murata")
    log.append("action_taken", "procurement_mgr", "Order shifted")

    is_valid, reason = log.verify_integrity()
    assert is_valid is True
    assert reason is None


def test_directly_editing_a_record_is_detected():
    """
    The core proof: an attacker with raw database access edits a past
    record directly (bypassing the AuditLog API entirely). This must be
    detected, not silently accepted.
    """
    log = AuditLog(db_path=TEST_DB)
    log.append("disruption_logged", "analyst_1", "Port strike at Keelung, 7 days")
    log.append("recommendation_issued", "system", "Monitor only, sufficient buffer")

    # Simulate direct database tampering: change the severity/details of
    # the FIRST entry, as if someone tried to downplay a disruption after
    # the fact, without going through the AuditLog API.
    conn = sqlite3.connect(TEST_DB)
    conn.execute(
        "UPDATE audit_log SET details = ? WHERE id = 1",
        ("Port strike at Keelung, 1 day (minor)",),
    )
    conn.commit()
    conn.close()

    is_valid, reason = log.verify_integrity()
    assert is_valid is False
    assert "Entry 1" in reason


def test_editing_the_most_recent_entry_is_also_detected():
    log = AuditLog(db_path=TEST_DB)
    log.append("disruption_logged", "analyst_1", "Original event")
    last = log.append("recommendation_issued", "system", "Original recommendation")

    conn = sqlite3.connect(TEST_DB)
    conn.execute("UPDATE audit_log SET actor = ? WHERE id = ?", ("someone_else", last.id))
    conn.commit()
    conn.close()

    is_valid, reason = log.verify_integrity()
    assert is_valid is False


def test_deleting_a_middle_entry_breaks_the_chain():
    log = AuditLog(db_path=TEST_DB)
    log.append("event_1", "analyst_1", "first")
    log.append("event_2", "analyst_1", "second")
    log.append("event_3", "analyst_1", "third")

    conn = sqlite3.connect(TEST_DB)
    conn.execute("DELETE FROM audit_log WHERE id = 2")
    conn.commit()
    conn.close()

    is_valid, reason = log.verify_integrity()
    assert is_valid is False
