"""
graph_agent.py
--------------
Graph Agent: answers "if X breaks, what does it affect?" by traversing
the supply chain graph.

Two backends are supported behind the same interface:
  - LocalGraphBackend: reads graph_data.json directly with plain Python
    traversal. No server needed -- this is what lets the cascade logic
    be unit-tested and demoed even before Neo4j is set up, and serves as
    a safety net if a live Neo4j connection fails during a demo.
  - Neo4jBackend: runs the same logical queries as real Cypher against a
    live Neo4j instance (see connect_neo4j() below).

Both backends expose the same three operations:
  trace_cascade(entity_type, entity_id) -> (affected_suppliers, affected_factories, affected_products)
  is_single_point_of_failure(entity_type, entity_id) -> bool | None
  assess_severity(entity_type, entity_id, duration_days) -> (severity, explanation)

Severity heuristic (deliberately simple and explainable, not a black box --
see the capstone report for why explainable scoring was chosen over an
opaque model here):

  Factory disruptions: severity scales with duration alone, since a
  factory stopping is a direct, undiluted hit to its own output.

  Route disruptions: severity scales with the delay relative to the
  route's normal transit time -- a 5-day delay matters little on a
  30-day sea route, a lot on a 3-day one.

  Port / Supplier disruptions: severity = f(single point of failure,
  duration, breadth of downstream impact). Each factor is scored
  independently and summed, so the reasoning behind any verdict is
  fully inspectable (see explain field in the result).
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

GRAPH_JSON_PATH = Path(__file__).parent.parent.parent / "data" / "graph_data.json"


@dataclass
class CascadeResult:
    entity_type: str
    entity_id: str
    affected_suppliers: list = field(default_factory=list)
    affected_factories: list = field(default_factory=list)
    affected_products: list = field(default_factory=list)


@dataclass
class SeverityResult:
    severity: str  # 'low' | 'medium' | 'high'
    explanation: str
    score_breakdown: dict


class LocalGraphBackend:
    """Pure-Python graph traversal over graph_data.json. No server required."""

    def __init__(self, path: Path = GRAPH_JSON_PATH):
        data = json.loads(Path(path).read_text())
        self.nodes = {n["id"]: n for n in data["nodes"]}
        self.edges = data["edges"]

    def _edges_from(self, node_id: str, edge_type: str) -> list:
        return [e for e in self.edges if e["from"] == node_id and e["type"] == edge_type]

    def _edges_to(self, node_id: str, edge_type: str) -> list:
        return [e for e in self.edges if e["to"] == node_id and e["type"] == edge_type]

    def trace_cascade(self, entity_type: str, entity_id: str) -> CascadeResult:
        if entity_type == "Supplier":
            affected_suppliers = [entity_id]
            factories = [e["to"] for e in self._edges_from(entity_id, "FEEDS")]

        elif entity_type == "Factory":
            affected_suppliers = []
            factories = [entity_id]

        elif entity_type == "Port":
            # Origin side: suppliers that ship out of this port (SHIPS_FROM), and
            # every factory those suppliers feed.
            affected_suppliers = [e["from"] for e in self._edges_to(entity_id, "SHIPS_FROM")]
            factory_set = set()
            for s in affected_suppliers:
                factory_set.update(e["to"] for e in self._edges_from(s, "FEEDS"))

            # Destination side: factories this port supplies (SUPPLIES), and the
            # suppliers whose routes arrive here AND feed one of those factories.
            # Without this, an outage at Yokohama/Hamburg/Rotterdam traced nothing.
            dest_factories = {e["to"] for e in self._edges_from(entity_id, "SUPPLIES")}
            if dest_factories:
                factory_set.update(dest_factories)
                for origin in (e["from"] for e in self._edges_to(entity_id, "ROUTE_TO")):
                    for s in (e["from"] for e in self._edges_to(origin, "SHIPS_FROM")):
                        fed = {e["to"] for e in self._edges_from(s, "FEEDS")}
                        if fed & dest_factories and s not in affected_suppliers:
                            affected_suppliers.append(s)
            factories = list(factory_set)

        elif entity_type == "Route":
            origin, dest = entity_id.split("->")
            suppliers_at_origin = [e["from"] for e in self._edges_to(origin, "SHIPS_FROM")]
            factories_at_dest = {e["to"] for e in self._edges_from(dest, "SUPPLIES")}

            affected_suppliers = []
            factory_set = set()
            for s in suppliers_at_origin:
                fed = {e["to"] for e in self._edges_from(s, "FEEDS")}
                overlap = fed & factories_at_dest
                if overlap:
                    affected_suppliers.append(s)
                    factory_set.update(overlap)
            factories = list(factory_set)

        else:
            raise ValueError(f"Unknown entity_type: {entity_type}")

        product_set = set()
        for f in factories:
            product_set.update(e["to"] for e in self._edges_from(f, "PRODUCES"))

        return CascadeResult(
            entity_type=entity_type,
            entity_id=entity_id,
            affected_suppliers=affected_suppliers,
            affected_factories=factories,
            affected_products=list(product_set),
        )

    def is_single_point_of_failure(self, entity_type: str, entity_id: str) -> bool | None:
        if entity_type == "Port":
            suppliers = [e["from"] for e in self._edges_to(entity_id, "SHIPS_FROM")]
            # Origin side: SPOF if none of these suppliers has an alternate port
            origin_spof = all(
                len(self._edges_from(s, "SHIPS_FROM")) <= 1 for s in suppliers
            ) and len(suppliers) > 0

            # Destination side: SPOF if this port is the ONLY port supplying at
            # least one factory it serves
            supplied = [e["to"] for e in self._edges_from(entity_id, "SUPPLIES")]
            dest_spof = any(
                len(self._edges_to(f, "SUPPLIES")) == 1 for f in supplied
            )
            return origin_spof or dest_spof

        if entity_type == "Supplier":
            fed_factories = [e["to"] for e in self._edges_from(entity_id, "FEEDS")]
            # SPOF if this supplier is the ONLY one feeding at least one of its factories
            return any(
                len(self._edges_to(f, "FEEDS")) == 1 for f in fed_factories
            )

        return None  # not a meaningful concept for Factory/Route

    def _route_baseline_days(self, entity_id: str) -> int | None:
        origin, dest = entity_id.split("->")
        for e in self.edges:
            if e["from"] == origin and e["to"] == dest and e["type"] == "ROUTE_TO":
                return e["days"]
        return None

    def assess_severity(self, entity_type: str, entity_id: str, duration_days: int) -> SeverityResult:
        cascade = self.trace_cascade(entity_type, entity_id)

        if entity_type == "Factory":
            if duration_days < 2:
                severity = "low"
            elif duration_days >= 14:
                severity = "high"
            else:
                severity = "medium"
            return SeverityResult(
                severity=severity,
                explanation=(
                    f"Factory disruption of {duration_days} days directly halts its own "
                    f"output ({len(cascade.affected_products)} product(s)); severity scales "
                    f"with duration alone."
                ),
                score_breakdown={"duration_days": duration_days},
            )

        if entity_type == "Route":
            baseline = self._route_baseline_days(entity_id)
            ratio = duration_days / baseline if baseline else 1.0
            severity = "low" if ratio < 0.3 else "medium" if ratio < 0.7 else "high"
            return SeverityResult(
                severity=severity,
                explanation=(
                    f"Delay of {duration_days} days on a route with {baseline}-day baseline "
                    f"transit time ({ratio:.0%} of normal transit) -- assessed relative to "
                    f"normal schedule, not in absolute terms."
                ),
                score_breakdown={"duration_days": duration_days, "baseline_days": baseline, "ratio": round(ratio, 2)},
            )

        # Port or Supplier
        spof = self.is_single_point_of_failure(entity_type, entity_id)
        spof_score = 2 if spof else 0
        duration_score = 2 if duration_days >= 21 else 1 if duration_days >= 7 else 0
        breadth_score = 1 if len(cascade.affected_factories) >= 3 else 0
        total = spof_score + duration_score + breadth_score

        severity = "high" if total >= 2 else "medium" if total == 1 else "low"

        return SeverityResult(
            severity=severity,
            explanation=(
                f"{'Single point of failure' if spof else 'Partial dependency (alternates exist)'} "
                f"+ {duration_days}-day duration + {len(cascade.affected_factories)} factories affected "
                f"-> score {total} -> {severity}."
            ),
            score_breakdown={
                "single_point_of_failure": spof,
                "spof_score": spof_score,
                "duration_score": duration_score,
                "breadth_score": breadth_score,
                "total": total,
            },
        )


def connect_neo4j(uri: str, user: str, password: str):
    """
    Returns a Neo4jBackend for use against a live instance, once one is
    running (e.g. via docker-compose). Not implemented in this sandbox
    (no network access to test against a live server) -- the interface
    matches LocalGraphBackend so swapping backends elsewhere requires no
    other code changes.
    """
    raise NotImplementedError(
        "Neo4jBackend requires a live Neo4j instance. Use LocalGraphBackend "
        "for development and testing; wire this up once Neo4j is running "
        "locally via docker-compose."
    )
