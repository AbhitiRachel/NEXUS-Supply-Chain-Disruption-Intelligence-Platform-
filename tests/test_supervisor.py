"""
test_supervisor.py
---------------------
Tests intent classification (routing correctness) and end-to-end
coordination across the Graph, RAG, and SQL agents.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.generate_graph_data import generate as generate_graph
from data.generate_sql_data import generate as generate_sql_data
from data.generate_documents import generate as generate_documents
from src.agents.supervisor import Supervisor, classify_intent


def setup_module(module):
    generate_graph()
    generate_sql_data()
    generate_documents()


def _fake_sql_generator(question, schema, error_feedback):
    return "SELECT COUNT(*) as n FROM shipments"


# --- Routing / classification tests -----------------------------------------

def test_classifies_cascade_question_as_graph():
    intents = classify_intent("What suppliers are affected if Keelung port shuts down?")
    assert "graph" in intents


def test_classifies_contract_question_as_rag():
    intents = classify_intent("What are the contract terms with TSMC?")
    assert "rag" in intents


def test_classifies_numeric_question_as_sql():
    intents = classify_intent("How many shipments were delayed last month?")
    assert "sql" in intents


def test_classifies_mixed_question_as_both_graph_and_rag():
    intents = classify_intent("If Keelung port shuts down, what does our contract say about penalties?")
    assert "graph" in intents
    assert "rag" in intents


def test_unclassifiable_question_falls_back_to_rag():
    intents = classify_intent("xyzabc random gibberish")
    assert intents == ["rag"]


# --- End-to-end coordination tests -------------------------------------------

def test_supervisor_answers_graph_question_with_cascade_data():
    supervisor = Supervisor(sql_generator_fn=_fake_sql_generator)
    result = supervisor.answer(
        "What is affected if Keelung port shuts down?",
        entity_type="Port", entity_id="PORT-KEELUNG", duration_days=7,
    )
    assert "graph" in result.intents_used
    assert result.graph_result is not None
    assert len(result.graph_result["cascade"].affected_suppliers) == 2
    assert result.graph_result["severity"].severity == "high"


def test_supervisor_answers_sql_question_with_real_data():
    supervisor = Supervisor(sql_generator_fn=_fake_sql_generator)
    result = supervisor.answer("How many shipments are there in total?")
    assert "sql" in result.intents_used
    assert result.sql_result.succeeded is True
    assert result.sql_result.rows[0]["n"] > 0


def test_supervisor_answers_document_question_with_retrieval():
    supervisor = Supervisor(sql_generator_fn=_fake_sql_generator)
    result = supervisor.answer("What are the contract terms for Infineon Kulim?")
    assert "rag" in result.intents_used
    assert len(result.rag_result) > 0
    assert result.rag_result[0].doc_type == "contract"


def test_supervisor_combines_multiple_agents_for_mixed_question():
    supervisor = Supervisor(sql_generator_fn=_fake_sql_generator)
    result = supervisor.answer(
        "If Keelung port shuts down, what does the contract say about penalties?",
        entity_type="Port", entity_id="PORT-KEELUNG", duration_days=7,
    )
    assert "graph" in result.intents_used
    assert "rag" in result.intents_used
    assert result.graph_result is not None
    assert result.rag_result is not None
    assert "|" in result.summary  # summary combines both agents' findings
