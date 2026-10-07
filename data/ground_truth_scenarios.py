"""
ground_truth_scenarios.py
---------------------------
Hand-defined "correct answer" scenarios, written BEFORE the agents exist.
This is deliberate: defining correctness up front (rather than checking
whatever the system happens to output) is what makes the evaluation
suite objective instead of circular.

Note on SC-004: originally this scenario listed all three Singapore-based
suppliers as affected by a Singapore->Rotterdam route disruption. While
building the Graph agent's cascade logic, testing against this scenario
revealed that was too loose -- only Infineon actually feeds a factory
reachable via Rotterdam (Philips Eindhoven); GlobalFoundries and Murata
feed factories reachable via other ports (Yokohama), so a Rotterdam-route
disruption doesn't actually touch their shipments. The scenario was
corrected to reflect the graph's actual dependency structure rather than
loosely grouping "any supplier at the origin port."
"""

SCENARIOS = [
    {
        "id": "SC-001",
        "description": "Port strike at Keelung (Taiwan) for 7 days",
        "disrupted_entity": {"type": "Port", "id": "PORT-KEELUNG"},
        "duration_days": 7,
        "expected_affected_suppliers": ["SUP-TSMC-HC", "SUP-UMC-TN"],
        "expected_affected_factories": [
            "FAC-SONY-KUMAMOTO", "FAC-DENSO-NAGOYA", "FAC-BOSCH-STUTTGART"
        ],
        "expected_affected_products": [
            "PROD-CAMERA-M4", "PROD-SENSOR-X1", "PROD-POWER-CTRL"
        ],
        "expected_severity": "high",
        "rationale": (
            "Keelung is the only port used by both Taiwan-based suppliers "
            "(TSMC, UMC), which together feed three of the four factories. "
            "No alternate port is configured for these suppliers in the "
            "synthetic graph, so this should be flagged as high severity."
        ),
    },
    {
        "id": "SC-002",
        "description": "Factory shutdown at Bosch Stuttgart for 3 days",
        "disrupted_entity": {"type": "Factory", "id": "FAC-BOSCH-STUTTGART"},
        "duration_days": 3,
        "expected_affected_suppliers": [],
        "expected_affected_factories": ["FAC-BOSCH-STUTTGART"],
        "expected_affected_products": ["PROD-POWER-CTRL"],
        "expected_severity": "medium",
        "rationale": (
            "A factory-level disruption only affects that factory's own "
            "product output; it should not cascade backward to suppliers. "
            "Short duration (3 days) and single product impacted keeps "
            "this at medium, not high, severity."
        ),
    },
    {
        "id": "SC-003",
        "description": "Supplier disruption at Murata Vietnam for 10 days",
        "disrupted_entity": {"type": "Supplier", "id": "SUP-MURATA-VN"},
        "duration_days": 10,
        "expected_affected_suppliers": ["SUP-MURATA-VN"],
        "expected_affected_factories": ["FAC-SONY-KUMAMOTO", "FAC-DENSO-NAGOYA"],
        "expected_affected_products": ["PROD-CAMERA-M4", "PROD-SENSOR-X1"],
        "expected_severity": "medium",
        "rationale": (
            "Murata feeds two factories, but both of those factories also "
            "receive components from other suppliers (TSMC, UMC, Samsung), "
            "so this is a partial-dependency case, not a single point of "
            "failure -- serious but not as severe as SC-001."
        ),
    },
    {
        "id": "SC-004",
        "description": "Route disruption: Singapore to Rotterdam sea route delayed 5 days",
        "disrupted_entity": {"type": "Route", "id": "PORT-SINGAPORE->PORT-ROTTERDAM"},
        "duration_days": 5,
        "expected_affected_suppliers": ["SUP-INFINEON-KL"],
        "expected_affected_factories": ["FAC-PHILIPS-EINDHOVEN"],
        "expected_affected_products": ["PROD-DISPLAY-D2"],
        "expected_severity": "low",
        "rationale": (
            "Only Infineon feeds a factory (Philips Eindhoven) that is "
            "reachable via Rotterdam; GlobalFoundries and Murata also ship "
            "from Singapore but feed factories reached via Yokohama, so "
            "they are unaffected by this specific route's disruption. The "
            "delay (5 days) is also short relative to the route's 24-day "
            "baseline transit time, keeping this at low severity."
        ),
    },
    {
        "id": "SC-005",
        "description": "Geopolitical restriction affecting Samsung Hwaseong Fab for 21 days",
        "disrupted_entity": {"type": "Supplier", "id": "SUP-SAMSUNG-HW"},
        "duration_days": 21,
        "expected_affected_suppliers": ["SUP-SAMSUNG-HW"],
        "expected_affected_factories": ["FAC-DENSO-NAGOYA", "FAC-PHILIPS-EINDHOVEN"],
        "expected_affected_products": ["PROD-SENSOR-X1", "PROD-DISPLAY-D2"],
        "expected_severity": "high",
        "rationale": (
            "Long duration (21 days, the longest in this scenario set) "
            "affecting two factories and two distinct product lines. "
            "Flagged high severity primarily due to duration, even though "
            "each factory has partial alternate sourcing."
        ),
    },
    {
        "id": "SC-006",
        "description": "Port closure at Yokohama (Japan) for 7 days",
        "disrupted_entity": {"type": "Port", "id": "PORT-YOKOHAMA"},
        "duration_days": 7,
        "expected_affected_suppliers": [
            "SUP-TSMC-HC", "SUP-UMC-TN", "SUP-SAMSUNG-HW", "SUP-MURATA-VN"
        ],
        "expected_affected_factories": ["FAC-SONY-KUMAMOTO", "FAC-DENSO-NAGOYA"],
        "expected_affected_products": ["PROD-CAMERA-M4", "PROD-SENSOR-X1"],
        "expected_severity": "high",
        "rationale": (
            "Yokohama is a destination port: it supplies Sony Kumamoto and Denso "
            "Nagoya, and receives routes from Keelung, Busan and Singapore. "
            "Suppliers affected are those on those routes that feed Sony or Denso "
            "(TSMC, UMC, Samsung, Murata); GlobalFoundries and Infineon feed only "
            "Bosch/Philips, which are served via other ports. Yokohama is the only "
            "port supplying both factories, so it is a single point of failure."
        ),
    },
    {
        "id": "SC-007",
        "description": "Port closure at Hamburg (Germany) for 7 days",
        "disrupted_entity": {"type": "Port", "id": "PORT-HAMBURG"},
        "duration_days": 7,
        "expected_affected_suppliers": ["SUP-TSMC-HC"],
        "expected_affected_factories": ["FAC-BOSCH-STUTTGART"],
        "expected_affected_products": ["PROD-POWER-CTRL"],
        "expected_severity": "high",
        "rationale": (
            "Hamburg supplies Bosch Stuttgart and receives only the Keelung route. "
            "Of the Keelung suppliers, only TSMC feeds Bosch (UMC feeds Sony only). "
            "Hamburg is Bosch's only supplying port, so it is a single point of failure."
        ),
    },
    {
        "id": "SC-008",
        "description": "Port closure at Rotterdam (Netherlands) for 7 days",
        "disrupted_entity": {"type": "Port", "id": "PORT-ROTTERDAM"},
        "duration_days": 7,
        "expected_affected_suppliers": ["SUP-INFINEON-KL", "SUP-SAMSUNG-HW"],
        "expected_affected_factories": ["FAC-PHILIPS-EINDHOVEN"],
        "expected_affected_products": ["PROD-DISPLAY-D2"],
        "expected_severity": "high",
        "rationale": (
            "Rotterdam supplies Philips Eindhoven and receives routes from Singapore "
            "and Busan. Of the suppliers on those routes, only Infineon and Samsung "
            "feed Philips (GlobalFoundries and Murata do not). Rotterdam is Philips' "
            "only supplying port, so it is a single point of failure."
        ),
    },
]


def get_scenario(scenario_id: str) -> dict:
    for s in SCENARIOS:
        if s["id"] == scenario_id:
            return s
    raise ValueError(f"Unknown scenario id: {scenario_id}")


if __name__ == "__main__":
    print(f"{len(SCENARIOS)} ground-truth scenarios defined:")
    for s in SCENARIOS:
        print(f"  {s['id']}: {s['description']} (expected severity: {s['expected_severity']})")
