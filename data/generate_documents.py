"""
generate_documents.py
-----------------------
Builds the unstructured document corpus that the RAG agent (ChromaDB)
retrieves from: contracts, shipping status reports, and disruption
notices, all referencing the same entity names as the graph and SQL data.
"""

import json
import random
from datetime import date, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.schema import SUPPLIERS, PORTS, FACTORIES, DISRUPTION_TYPES

OUT_DIR = Path(__file__).parent / "documents"
OUT_DIR.mkdir(exist_ok=True)


CONTRACT_TEMPLATE = """SUPPLY AGREEMENT SUMMARY
Supplier: {supplier_name} ({supplier_id})
Counterparty: NEXUS Electronics Group
Effective date: {effective_date}
Term: 24 months, auto-renewing

Key terms:
- Minimum order commitment: {moq} units per quarter
- Lead time SLA: {lead_time} days from order confirmation to port handoff
- Force majeure clause covers: {disruption_1}, {disruption_2}
- Penalty for late delivery beyond SLA: {penalty}% of shipment value per week delayed
- Alternate sourcing clause: counterparty may source up to {alt_pct}% of volume from
  an alternate supplier without breach if lead time SLA is missed twice in a quarter.

Notes: This supplier has been a partner since {partner_since} with a delivery
reliability track record of {reliability}% on-time over the past 12 months.
"""

DISRUPTION_NOTICE_TEMPLATE = """DISRUPTION NOTICE
Date: {notice_date}
Affected entity: {entity_name} ({entity_id})
Type: {disruption_type}

Summary: {entity_name} has reported an operational disruption classified as
{disruption_type}, expected to last approximately {duration} days beginning
{start_date}. Preliminary assessment indicates {severity} impact on
throughput.

Recommended monitoring: shipments and orders routed through or dependent on
{entity_name} should be flagged for review until normal operations resume.
Downstream partners should assess buffer inventory levels accordingly.
"""

SHIPPING_REPORT_TEMPLATE = """PORT STATUS REPORT
Port: {port_name} ({port_id})
Reporting period: {period}

Current throughput: {throughput}% of nominal capacity
Congestion level: {congestion}
Average dwell time: {dwell} days

Comments: {port_name} continues to handle {category} cargo volumes typical
for this period. {extra_note}
"""


def _rand_date_within(days_back=180):
    return (date.today() - timedelta(days=random.randint(0, days_back))).isoformat()


def generate_contracts():
    docs = []
    for sid, name, country, category in SUPPLIERS:
        text = CONTRACT_TEMPLATE.format(
            supplier_name=name,
            supplier_id=sid,
            effective_date=_rand_date_within(400),
            moq=random.choice([50000, 100000, 150000, 200000]),
            lead_time=random.randint(14, 45),
            disruption_1=random.choice(DISRUPTION_TYPES),
            disruption_2=random.choice(DISRUPTION_TYPES),
            penalty=random.choice([1, 2, 3, 5]),
            alt_pct=random.choice([10, 15, 20, 25]),
            partner_since=random.randint(2018, 2024),
            reliability=random.randint(82, 98),
        )
        fname = f"contract_{sid}.txt"
        (OUT_DIR / fname).write_text(text)
        docs.append({"filename": fname, "doc_type": "contract", "entity_id": sid,
                     "entity_name": name})
    return docs


def generate_disruption_notices(n=15):
    docs = []
    entity_pool = (
        [(sid, name) for sid, name, *_ in SUPPLIERS]
        + [(pid, name) for pid, name, *_ in PORTS]
        + [(fid, name) for fid, name, *_ in FACTORIES]
    )
    for i in range(n):
        entity_id, entity_name = random.choice(entity_pool)
        disruption_type = random.choice(DISRUPTION_TYPES)
        start = _rand_date_within(90)
        text = DISRUPTION_NOTICE_TEMPLATE.format(
            notice_date=_rand_date_within(90),
            entity_name=entity_name,
            entity_id=entity_id,
            disruption_type=disruption_type,
            duration=random.randint(2, 14),
            start_date=start,
            severity=random.choice(["low", "moderate", "significant"]),
        )
        fname = f"disruption_notice_{i:03d}_{entity_id}.txt"
        (OUT_DIR / fname).write_text(text)
        docs.append({"filename": fname, "doc_type": "disruption_notice",
                     "entity_id": entity_id, "entity_name": entity_name})
    return docs


def generate_shipping_reports():
    docs = []
    for pid, name, country in PORTS:
        text = SHIPPING_REPORT_TEMPLATE.format(
            port_name=name,
            port_id=pid,
            period=f"{_rand_date_within(30)} to {date.today().isoformat()}",
            throughput=random.randint(65, 100),
            congestion=random.choice(["low", "moderate", "elevated", "high"]),
            dwell=round(random.uniform(1.5, 6.0), 1),
            category=random.choice(["mixed electronics", "semiconductor", "general"]),
            extra_note=random.choice([
                "No significant delays reported this period.",
                "Minor customs processing delays noted for outbound cargo.",
                "Weather monitoring in effect; no closures at this time.",
            ]),
        )
        fname = f"shipping_report_{pid}.txt"
        (OUT_DIR / fname).write_text(text)
        docs.append({"filename": fname, "doc_type": "shipping_report", "entity_id": pid,
                     "entity_name": name})
    return docs


def generate():
    random.seed(43)  # inside generate(), not module level -- so repeated
                      # calls in the same process are still deterministic
    all_docs = []
    all_docs += generate_contracts()
    all_docs += generate_disruption_notices()
    all_docs += generate_shipping_reports()

    (OUT_DIR / "documents_index.json").write_text(json.dumps(all_docs, indent=2))
    print(f"Generated {len(all_docs)} documents into {OUT_DIR}")
    for doc_type in ["contract", "disruption_notice", "shipping_report"]:
        count = sum(1 for d in all_docs if d["doc_type"] == doc_type)
        print(f"  {doc_type}: {count}")


if __name__ == "__main__":
    generate()
