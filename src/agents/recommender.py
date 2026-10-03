"""
recommender.py
---------------
Recommendation layer: turns a Simulation agent's what-if result into a
plain-English recommendation with a fully inspectable rationale.

Deliberately NOT a black-box optimizer -- every recommendation states
exactly which facts drove it (buffer status, cost at risk, alternate
supplier availability) so it can be defended in a viva or trusted by a
business stakeholder who isn't going to take "the algorithm said so."

Recommendation logic (in priority order):
  1. If ALL affected factories have sufficient buffer (days_of_cover >=
     duration_days): recommend MONITOR ONLY. Urgency is low regardless
     of the graph-severity label, because operations won't actually be
     interrupted before the disruption resolves.
  2. If some factories are at risk AND an alternate supplier already
     feeds that factory: recommend SHIFT ORDERS to the alternate --
     lowest-friction real option, since no new supplier qualification
     is needed.
  3. If some factories are at risk AND no alternate supplier exists
     (true single point of failure): recommend EXPEDITE / ACTIVATE
     CONTRACT CLAUSE -- the contract's alternate-sourcing clause (see
     the synthetic contract documents) is the fallback lever available.
"""

from dataclasses import dataclass, field

from src.agents.graph_agent import LocalGraphBackend
from src.agents.simulation_agent import WhatIfResult


@dataclass
class AlternateSupplierOption:
    supplier_id: str
    supplier_name: str
    already_feeds_factory: bool
    other_factories_served: int  # proxy for scale/reliability -- transparently stated, not hidden


@dataclass
class Recommendation:
    action: str  # 'monitor_only' | 'shift_to_alternate' | 'expedite_or_activate_clause'
    rationale: str
    alternate_options: list = field(default_factory=list)
    estimated_cost_usd: float = 0.0


class Recommender:
    def __init__(self):
        self.graph = LocalGraphBackend()

    def _find_alternates(self, factory_id: str, exclude_supplier_id: str) -> list[AlternateSupplierOption]:
        feeding_suppliers = [
            e["from"] for e in self.graph._edges_to(factory_id, "FEEDS")
            if e["from"] != exclude_supplier_id
        ]
        options = []
        for sid in feeding_suppliers:
            other_factories = len(self.graph._edges_from(sid, "FEEDS")) - 1  # minus this factory
            options.append(
                AlternateSupplierOption(
                    supplier_id=sid,
                    supplier_name=self.graph.nodes[sid]["name"],
                    already_feeds_factory=True,
                    other_factories_served=max(other_factories, 0),
                )
            )
        # Rank by scale served elsewhere (transparent proxy, not a hidden score)
        return sorted(options, key=lambda o: -o.other_factories_served)

    def recommend(self, whatif: WhatIfResult, disrupted_entity_id: str) -> Recommendation:
        at_risk_statuses = [b for b in whatif.buffer_statuses if b.at_risk]

        if not at_risk_statuses:
            min_buffer = min((b.days_of_cover for b in whatif.buffer_statuses), default=None)
            return Recommendation(
                action="monitor_only",
                rationale=(
                    f"All affected factories have sufficient inventory buffer to absorb "
                    f"this disruption without a production interruption "
                    f"(lowest buffer: {min_buffer} days of cover). No immediate sourcing "
                    f"action needed. Estimated ${whatif.total_estimated_cost_usd:,.2f} in "
                    f"shipment value is still at risk if the disruption extends beyond "
                    f"current buffer levels -- recommend monitoring and re-assessing if "
                    f"duration increases."
                ),
                estimated_cost_usd=whatif.total_estimated_cost_usd,
            )

        # At least one factory is genuinely at risk of stockout
        all_alternates = []
        for status in at_risk_statuses:
            alternates = self._find_alternates(status.factory_id, disrupted_entity_id)
            all_alternates.extend(alternates)

        # De-duplicate by supplier_id, keep best (most other-factory experience)
        seen = {}
        for opt in all_alternates:
            if opt.supplier_id not in seen or opt.other_factories_served > seen[opt.supplier_id].other_factories_served:
                seen[opt.supplier_id] = opt
        unique_alternates = sorted(seen.values(), key=lambda o: -o.other_factories_served)

        at_risk_summary = ", ".join(
            f"{b.factory_id} (stockout in ~{b.days_until_stockout}d)" for b in at_risk_statuses
        )

        if unique_alternates:
            top = unique_alternates[0]
            return Recommendation(
                action="shift_to_alternate",
                rationale=(
                    f"{at_risk_summary} will exhaust buffer stock before this disruption "
                    f"resolves. {top.supplier_name} already supplies other factories and "
                    f"can likely absorb additional volume without new supplier "
                    f"qualification -- recommend shifting orders there for the affected "
                    f"product(s). Estimated ${whatif.total_estimated_cost_usd:,.2f} in "
                    f"shipment value is at risk if no action is taken."
                ),
                alternate_options=unique_alternates,
                estimated_cost_usd=whatif.total_estimated_cost_usd,
            )

        return Recommendation(
            action="expedite_or_activate_clause",
            rationale=(
                f"{at_risk_summary} will exhaust buffer stock before this disruption "
                f"resolves, and no alternate supplier is currently configured for the "
                f"affected factory/product -- this is a genuine single point of failure. "
                f"Recommend expediting shipment via alternate routing where possible, or "
                f"activating the contract's alternate-sourcing clause (see supplier "
                f"contract documents) to qualify a new source. Estimated "
                f"${whatif.total_estimated_cost_usd:,.2f} in shipment value at risk."
            ),
            estimated_cost_usd=whatif.total_estimated_cost_usd,
        )
