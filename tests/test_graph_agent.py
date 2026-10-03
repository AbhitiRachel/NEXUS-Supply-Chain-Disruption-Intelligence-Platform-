"""
test_graph_agent.py
---------------------
Validates the Graph agent's cascade tracing and severity assessment
against all hand-written ground-truth scenarios. This is the single most
important test file in the project: if these pass, the Graph agent's core
reasoning is verifiably correct, not just plausible-looking.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.graph_agent import LocalGraphBackend
from data.generate_graph_data import generate as generate_graph
from data.ground_truth_scenarios import SCENARIOS


def setup_module(module):
    generate_graph()


def test_all_ground_truth_scenarios_match():
    g = LocalGraphBackend()
    failures = []

    for s in SCENARIOS:
        entity = s["disrupted_entity"]
        result = g.trace_cascade(entity["type"], entity["id"])
        severity = g.assess_severity(entity["type"], entity["id"], s["duration_days"])

        checks = {
            "suppliers": sorted(result.affected_suppliers) == sorted(s["expected_affected_suppliers"]),
            "factories": sorted(result.affected_factories) == sorted(s["expected_affected_factories"]),
            "products": sorted(result.affected_products) == sorted(s["expected_affected_products"]),
            "severity": severity.severity == s["expected_severity"],
        }
        if not all(checks.values()):
            failures.append((s["id"], checks))

    assert not failures, f"Scenario mismatches: {failures}"


def test_factory_disruption_never_cascades_to_suppliers():
    """A factory breaking shouldn't be reported as affecting suppliers upstream."""
    g = LocalGraphBackend()
    result = g.trace_cascade("Factory", "FAC-BOSCH-STUTTGART")
    assert result.affected_suppliers == []


def test_single_point_of_failure_detection_for_port():
    g = LocalGraphBackend()
    # Keelung is used exclusively by TSMC and UMC in the synthetic graph
    assert g.is_single_point_of_failure("Port", "PORT-KEELUNG") is True


def test_single_point_of_failure_detection_for_shared_supplier():
    g = LocalGraphBackend()
    # Murata's factories all have other suppliers too -- not a SPOF
    assert g.is_single_point_of_failure("Supplier", "SUP-MURATA-VN") is False


def test_route_severity_scales_with_relative_not_absolute_delay():
    g = LocalGraphBackend()
    short_route_severity = g.assess_severity(
        "Route", "PORT-SINGAPORE->PORT-ROTTERDAM", duration_days=5
    )
    # 5 days on a 24-day route is a small fraction -> should be low, not high
    assert short_route_severity.severity == "low"
