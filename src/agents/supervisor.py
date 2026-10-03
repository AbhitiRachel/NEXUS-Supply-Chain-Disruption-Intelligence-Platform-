"""
supervisor.py
-------------
Supervisor Agent: receives a plain-language question, decides which
specialized agent(s) it needs (Graph, RAG, SQL), calls them, and combines
their outputs into one coherent answer.

Design note for the report: this is written as plain Python routing
logic rather than a live LangGraph StateGraph, because langgraph isn't
installable in this sandbox (no network access). The routing DECISION
and multi-agent COORDINATION -- the actual orchestration-level autonomy
that matters for the "agentic AI" story -- is fully built and tested
here. Porting this into an actual LangGraph StateGraph is a mechanical
step (each route_to_* method becomes a graph node, classify_intent's
output becomes the conditional edge) once langgraph is installed
locally; the decision logic itself does not need to change.

Routing is rule-based and keyword-driven, not an LLM call -- deliberate,
same philosophy as the Planner in the earlier CloudGuard project: a
routing decision should be fast, free, and fully explainable. The
report should be explicit that this is a deliberate simplicity choice,
not an oversight; an LLM-based router is a natural upgrade path if a
question's intent is genuinely ambiguous.
"""

import re
from dataclasses import dataclass, field

from src.agents.graph_agent import LocalGraphBackend
from src.agents.rag_agent import LocalRAGBackend
from src.agents.sql_agent import answer_question as sql_answer_question

GRAPH_KEYWORDS = [
    "affect", "affects", "affected", "cascade", "disrupt", "disruption",
    "impact", "downstream", "if .* (shuts down|breaks|fails|closes)",
    "what happens if", "which suppliers", "which factories", "which products",
]
RAG_KEYWORDS = [
    "contract", "policy", "clause", "terms", "agreement", "reliability",
    "report", "document", "notice", "sla", "penalty",
]
SQL_KEYWORDS = [
    "how much", "how many", "cost", "average", "total", "count",
    "inventory", "delay days", "on time", "on-time", "spend", "spent",
]


@dataclass
class SupervisorResult:
    question: str
    intents_used: list = field(default_factory=list)
    graph_result: object = None
    rag_result: object = None
    sql_result: object = None
    summary: str = ""


def classify_intent(question: str) -> list[str]:
    """
    Returns a list of intents from {'graph', 'rag', 'sql'} -- a question
    can trigger more than one (e.g. asking about both a disruption's
    reach AND its documented contract terms).
    """
    q = question.lower()
    intents = []

    if any(re.search(kw, q) for kw in GRAPH_KEYWORDS):
        intents.append("graph")
    if any(kw in q for kw in RAG_KEYWORDS):
        intents.append("rag")
    if any(kw in q for kw in SQL_KEYWORDS):
        intents.append("sql")

    if not intents:
        # Default fallback: an unclassified question is most likely
        # asking for document context rather than a precise number or a
        # cascade trace -- RAG is the safest generalist fallback.
        intents.append("rag")

    return intents


class Supervisor:
    def __init__(self, sql_generator_fn):
        """
        sql_generator_fn: the SQL-generation function to use (e.g.
        groq_sql_generator in production, or a fake for testing). This
        keeps the Supervisor decoupled from any specific LLM provider.
        """
        self.graph_agent = LocalGraphBackend()
        self.rag_agent = LocalRAGBackend()
        self.sql_generator_fn = sql_generator_fn

    def answer(self, question: str, entity_type: str = None, entity_id: str = None,
               duration_days: int = None) -> SupervisorResult:
        intents = classify_intent(question)
        result = SupervisorResult(question=question, intents_used=intents)
        summary_parts = []

        if "graph" in intents and entity_type and entity_id:
            cascade = self.graph_agent.trace_cascade(entity_type, entity_id)
            severity = None
            if duration_days is not None:
                severity = self.graph_agent.assess_severity(entity_type, entity_id, duration_days)
            result.graph_result = {"cascade": cascade, "severity": severity}
            summary_parts.append(
                f"Cascade trace: {len(cascade.affected_suppliers)} supplier(s), "
                f"{len(cascade.affected_factories)} factory(ies), "
                f"{len(cascade.affected_products)} product(s) affected."
                + (f" Severity: {severity.severity} ({severity.explanation})" if severity else "")
            )

        if "rag" in intents:
            doc_type = None
            if "contract" in question.lower() or "terms" in question.lower():
                doc_type = "contract"
            elif "report" in question.lower() or "congestion" in question.lower():
                doc_type = "shipping_report"

            # Cross-agent enrichment: if the Graph agent already identified
            # which suppliers are actually affected, focus the document
            # search on THOSE suppliers rather than the raw question text
            # alone -- otherwise a generic question can retrieve an
            # unrelated supplier's document with a misleadingly plausible
            # (but low) similarity score.
            search_query = question
            if result.graph_result and result.graph_result["cascade"].affected_suppliers:
                affected_names = ", ".join(
                    self.graph_agent.nodes[sid]["name"]
                    for sid in result.graph_result["cascade"].affected_suppliers
                    if sid in self.graph_agent.nodes
                )
                search_query = f"{question} {affected_names}"

            docs = self.rag_agent.retrieve(search_query, top_k=2, doc_type=doc_type)
            result.rag_result = docs
            if docs:
                summary_parts.append(
                    f"Relevant document: {docs[0].filename} (score {docs[0].score})"
                )

        if "sql" in intents:
            sql_result = sql_answer_question(question, self.sql_generator_fn)
            result.sql_result = sql_result
            if sql_result.succeeded:
                summary_parts.append(
                    f"Data query result: {sql_result.rows} "
                    f"(via {sql_result.attempts_used} attempt(s)"
                    + (", self-corrected" if sql_result.was_self_corrected else "")
                    + ")"
                )
            else:
                summary_parts.append("Data query could not be completed after retries.")

        result.summary = " | ".join(summary_parts) if summary_parts else "No applicable agent found a result."
        return result
