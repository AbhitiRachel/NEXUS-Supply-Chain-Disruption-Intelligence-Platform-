"""
test_simulation_and_recommender.py
--------------------------------------
Tests the Simulation agent's buffer/cost math and the Recommender's
decision logic against real generated data.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.generate_graph_data import generate as generate_graph
from data.generate_sql_data import generate as generate_sql_data
from src.agents.simulation_agent import SimulationAgent
from src.agents.recommender import Recommender


def setup_module(module):
    generate_graph()
    generate_sql_data()


def test_whatif_returns_cascade_consistent_with_graph_agent():
    sim = SimulationAgent()
    result = sim.run_whatif("Port", "PORT-KEELUNG", duration_days=7)
    assert set(result.cascade.affected_suppliers) == {"SUP-TSMC-HC", "SUP-UMC-TN"}
    assert result.severity.severity == "high"


def test_buffer_status_correctly_flags_short_disruption_as_safe():
    sim = SimulationAgent()
    result = sim.run_whatif("Port", "PORT-KEELUNG", duration_days=7)
    # All factories in the synthetic data carry well over a week of buffer
    assert all(not b.at_risk for b in result.buffer_statuses)


def test_buffer_status_correctly_flags_long_disruption_as_risky():
    sim = SimulationAgent()
    result = sim.run_whatif("Port", "PORT-KEELUNG", duration_days=60)
    # A 60-day disruption should exceed buffer for at least one factory
    assert any(b.at_risk for b in result.buffer_statuses)


def test_cost_estimate_is_positive_and_scales_with_duration():
    sim = SimulationAgent()
    short = sim.run_whatif("Port", "PORT-KEELUNG", duration_days=7)
    long = sim.run_whatif("Port", "PORT-KEELUNG", duration_days=60)
    assert short.total_estimated_cost_usd > 0
    assert long.total_estimated_cost_usd > short.total_estimated_cost_usd


def test_recommender_suggests_monitor_only_when_fully_buffered():
    sim = SimulationAgent()
    rec = Recommender()
    result = sim.run_whatif("Port", "PORT-KEELUNG", duration_days=7)
    recommendation = rec.recommend(result, disrupted_entity_id="PORT-KEELUNG")
    assert recommendation.action == "monitor_only"


def test_recommender_suggests_alternate_when_buffer_exhausted_and_alternate_exists():
    sim = SimulationAgent()
    rec = Recommender()
    result = sim.run_whatif("Port", "PORT-KEELUNG", duration_days=60)
    recommendation = rec.recommend(result, disrupted_entity_id="SUP-TSMC-HC")
    assert recommendation.action == "shift_to_alternate"
    assert len(recommendation.alternate_options) > 0


def test_recommendation_rationale_mentions_actual_cost_figure():
    sim = SimulationAgent()
    rec = Recommender()
    result = sim.run_whatif("Port", "PORT-KEELUNG", duration_days=7)
    recommendation = rec.recommend(result, disrupted_entity_id="PORT-KEELUNG")
    assert "$" in recommendation.rationale
    assert recommendation.estimated_cost_usd > 0


def test_alternate_options_never_include_the_disrupted_supplier_itself():
    sim = SimulationAgent()
    rec = Recommender()
    result = sim.run_whatif("Supplier", "SUP-TSMC-HC", duration_days=60)
    recommendation = rec.recommend(result, disrupted_entity_id="SUP-TSMC-HC")
    alt_ids = [o.supplier_id for o in recommendation.alternate_options]
    assert "SUP-TSMC-HC" not in alt_ids
