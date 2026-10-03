"""
simulation_agent.py
---------------------
Simulation Agent: runs a hypothetical ("what-if") disruption through the
Graph agent's cascade logic, then adds two things a plain cascade trace
doesn't give you:

1. Buffer check -- does the affected factory have enough inventory
   (days_of_cover) to absorb the disruption before running out? A
   7-day port strike matters a lot less if the factory has 20 days of
   buffer stock than if it has 2.

2. Dollar cost estimate -- using REAL historical shipment data (average
   cost per shipment, shipment frequency) for the affected supplier(s),
   estimates the dollar value of shipments at risk during the disruption
   window. This is deliberately a simple, transparent estimate (frequency
   x average cost x duration), not a black-box financial model -- the
   report should be explicit that this is an estimate methodology, not a
   precise forecast, and state its assumptions plainly.
"""

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from src.agents.graph_agent import LocalGraphBackend, CascadeResult, SeverityResult

DB_PATH = Path(__file__).parent.parent.parent / "data" / "nexus.db"


@dataclass
class BufferStatus:
    factory_id: str
    product_id: str
    days_of_cover: float
    at_risk: bool
    days_until_stockout: float | None  # None if not at risk


@dataclass
class CostEstimate:
    supplier_id: str
    avg_cost_per_shipment: float
    shipments_per_period: float
    estimated_shipments_affected: float
    estimated_value_at_risk_usd: float
    assumptions: str


@dataclass
class WhatIfResult:
    cascade: CascadeResult
    severity: SeverityResult
    buffer_statuses: list = field(default_factory=list)
    cost_estimates: list = field(default_factory=list)
    total_estimated_cost_usd: float = 0.0


class SimulationAgent:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.graph = LocalGraphBackend()

    def _get_latest_inventory(self, factory_id: str, product_id: str) -> float | None:
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            """SELECT days_of_cover FROM inventory
               WHERE factory_id = ? AND product_id = ?
               ORDER BY date DESC LIMIT 1""",
            (factory_id, product_id),
        ).fetchone()
        conn.close()
        return row[0] if row else None

    def _get_shipment_stats(self, supplier_id: str, history_days: int = 90) -> tuple[float, float]:
        """Returns (avg_cost_per_shipment, shipments_per_day) from real history."""
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT COUNT(*) as n, AVG(cost_usd) as avg_cost FROM shipments WHERE supplier_id = ?",
            (supplier_id,),
        ).fetchone()
        conn.close()
        n, avg_cost = row
        shipments_per_day = n / history_days if n else 0.0
        return (avg_cost or 0.0), shipments_per_day

    def run_whatif(self, entity_type: str, entity_id: str, duration_days: int) -> WhatIfResult:
        cascade = self.graph.trace_cascade(entity_type, entity_id)
        severity = self.graph.assess_severity(entity_type, entity_id, duration_days)

        # --- Buffer check for each affected factory/product pair ---
        buffer_statuses = []
        for factory_id in cascade.affected_factories:
            for product_id in self.graph._edges_from(factory_id, "PRODUCES"):
                pid = product_id["to"]
                days_of_cover = self._get_latest_inventory(factory_id, pid)
                if days_of_cover is None:
                    continue
                at_risk = days_of_cover < duration_days
                buffer_statuses.append(
                    BufferStatus(
                        factory_id=factory_id,
                        product_id=pid,
                        days_of_cover=days_of_cover,
                        at_risk=at_risk,
                        days_until_stockout=(
                            round(duration_days - days_of_cover, 1) if at_risk else None
                        ),
                    )
                )

        # --- Cost estimate per affected supplier ---
        cost_estimates = []
        relevant_suppliers = cascade.affected_suppliers or (
            [entity_id] if entity_type == "Supplier" else []
        )
        for supplier_id in relevant_suppliers:
            avg_cost, shipments_per_day = self._get_shipment_stats(supplier_id)
            estimated_shipments = shipments_per_day * duration_days
            estimated_value = round(estimated_shipments * avg_cost, 2)
            cost_estimates.append(
                CostEstimate(
                    supplier_id=supplier_id,
                    avg_cost_per_shipment=round(avg_cost, 2),
                    shipments_per_period=round(shipments_per_day, 3),
                    estimated_shipments_affected=round(estimated_shipments, 2),
                    estimated_value_at_risk_usd=estimated_value,
                    assumptions=(
                        f"Based on {supplier_id}'s historical average shipment frequency "
                        f"and cost over the last 90 days of data, projected across the "
                        f"{duration_days}-day disruption window. This estimates shipment "
                        f"VALUE AT RISK (delayed/rerouted), not a confirmed financial loss -- "
                        f"actual loss depends on whether the order is fulfilled late, from an "
                        f"alternate source, or not at all."
                    ),
                )
            )

        total_cost = round(sum(c.estimated_value_at_risk_usd for c in cost_estimates), 2)

        return WhatIfResult(
            cascade=cascade,
            severity=severity,
            buffer_statuses=buffer_statuses,
            cost_estimates=cost_estimates,
            total_estimated_cost_usd=total_cost,
        )
