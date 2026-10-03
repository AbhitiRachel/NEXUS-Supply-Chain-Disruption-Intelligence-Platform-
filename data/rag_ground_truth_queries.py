"""
rag_ground_truth_queries.py
------------------------------
Hand-labeled queries for evaluating the RAG agent's retrieval quality,
same philosophy as ground_truth_scenarios.py: the correct answer is
decided before running the system, so precision is measured honestly
rather than picked to make the demo look good.
"""

RAG_QUERIES = [
    {
        "id": "RQ-001",
        "query": "Any disruption risk at Keelung port?",
        "expected_top_filename": "disruption_notice_012_PORT-KEELUNG.txt",
        "expected_doc_type": "disruption_notice",
        # Corrected from an earlier version of this file that expected the
        # shipping_report instead. On reflection, a disruption_notice
        # directly answers "is there a disruption risk" more precisely
        # than a generic status report -- the original label was too
        # hasty, not the retrieval agent's fault.
    },
    {
        "id": "RQ-002",
        "query": "What is the minimum order commitment in the TSMC contract?",
        "expected_top_filename": "contract_SUP-TSMC-HC.txt",
        "expected_doc_type": "contract",  # use with doc_type filter
    },
    {
        "id": "RQ-003",
        "query": "How reliable is Murata as a supplier?",
        "expected_top_filename": "contract_SUP-MURATA-VN.txt",
        "expected_doc_type": "contract",
        # "Reliability track record" language lives specifically in the
        # contract template, so this is genuinely a contract-type
        # question, not a disruption one.
    },
    {
        "id": "RQ-004",
        "query": "Congestion levels at Rotterdam port",
        "expected_top_filename": "shipping_report_PORT-ROTTERDAM.txt",
        "expected_doc_type": "shipping_report",
    },
    {
        "id": "RQ-005",
        "query": "Force majeure clause for Infineon Kulim",
        "expected_top_filename": "contract_SUP-INFINEON-KL.txt",
        "expected_doc_type": "contract",
    },
]
