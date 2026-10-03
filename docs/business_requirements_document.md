# Business Requirements Document (BRD)
## NEXUS — Supply Chain Disruption Intelligence Platform

**Prepared as part of an M.Tech Data Science capstone.** This document is
written in the format a Business Analyst would produce when scoping this
system for a stakeholder, and is included as a project artifact
demonstrating requirements-definition and business-framing skills
alongside the technical build.

---

## 1. Executive Summary

Global electronics manufacturers depend on multi-tier international
supply chains — chip fabrication in Taiwan/Southeast Asia, shipped
through regional ports, assembled into finished products in Japan and
Europe. A disruption at any single point (a port strike, a factory
shutdown, a supplier outage) can cascade into delayed production and
lost revenue days or weeks later, often before the business has a clear
picture of the scale of impact.

NEXUS is proposed as an internal decision-support tool that lets supply
chain and operations analysts ask plain-language questions about
disruption risk and receive a fast, evidence-based assessment: what's
affected, how severe, and what to do about it — without needing to
manually cross-reference contracts, shipment logs, and supplier reports
by hand.

## 2. Business Problem

- Disruption impact assessment today is manual, slow, and spread across
  multiple systems (contracts, shipment tracking, supplier
  communications).
- Analysts often cannot quickly answer "how bad is this, really?" for a
  given disruption — severity assessment is informal and inconsistent
  between analysts.
- Response decisions (reroute, switch supplier, absorb the delay) are
  made without a consistent, explainable method for comparing
  alternatives.

## 3. Stakeholders

| Stakeholder | Interest |
|---|---|
| Supply Chain Operations Analyst | Primary user; needs fast, trustworthy disruption assessments |
| Procurement Manager | Needs to evaluate alternate-supplier recommendations |
| Finance / FP&A | Needs cost-impact estimates for disruption events |
| Executive Leadership | Needs a high-level risk summary, not operational detail |

## 4. Business Objectives

1. Reduce the time to assess a disruption's severity and downstream
   impact from hours of manual cross-referencing to a single query.
2. Provide a consistent, explainable severity assessment method — not
   ad hoc analyst judgment that varies person to person.
3. Surface an estimated cost impact in dollar terms, so operational
   disruptions can be prioritized using the same language Finance uses.
4. Maintain an auditable, tamper-evident record of disruption events and
   the recommendations made in response, for internal review and
   compliance purposes.

## 5. Functional Requirements

| ID | Requirement |
|---|---|
| FR-1 | System shall accept a plain-language question about a disruption and return affected suppliers, factories, and products. |
| FR-2 | System shall assign a severity level (low/medium/high) with a stated, inspectable reason — not an unexplained score. |
| FR-3 | System shall retrieve relevant supporting documents (contracts, shipping reports, disruption notices) for a given query. |
| FR-4 | System shall answer structured data questions (costs, delays, inventory) by querying operational records directly. |
| FR-5 | System shall estimate the dollar cost impact of a disruption based on affected shipment value and delay duration. |
| FR-6 | System shall recommend a response (e.g. alternate supplier, reroute) with a transparent rationale for the recommendation. |
| FR-7 | System shall maintain a tamper-evident log of disruption events and recommendations for audit purposes. |
| FR-8 | System shall present results through a dashboard usable by non-technical stakeholders (no query language required). |

## 6. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-1 | Responses should return within a few seconds for typical queries. |
| NFR-2 | The system must run at zero infrastructure cost, using open-source and free-tier components only. |
| NFR-3 | Access should be role-restricted (viewer vs. analyst) at a basic level. |
| NFR-4 | The system must resist malicious or manipulative input to its natural-language interface. |

## 7. Success Metrics (Business-Defined)

- **Assessment turnaround**: query-to-answer time, target under 10 seconds
  for a standard disruption query.
- **Severity consistency**: agreement rate between system-assigned
  severity and hand-reviewed ground-truth scenarios, target 90%+.
- **Retrieval relevance**: percentage of document retrievals that surface
  the correct supporting document for a given question, target 90%+.
- **Recommendation defensibility**: percentage of recommendations that
  include a clear, inspectable rationale (not a black-box output),
  target 100% — this is a hard requirement, not a stretch goal.

## 8. Scope

**In scope:** disruption assessment, document retrieval, structured data
querying, cost estimation, response recommendation, audit logging, a
basic dashboard.

**Out of scope (for this phase):** real-time data feed integration with
live carrier/logistics APIs, multi-language support, mobile app
interface, integration with a live ERP system. These are noted as
natural extensions for a production version, not gaps in the current
build.

## 9. Assumptions and Constraints

- This capstone build uses synthetic data standing in for real
  operational systems, since no live enterprise data is available for an
  individual academic project.
- Zero budget: all components must use free-tier or open-source
  technology.
- Single developer, one-month timeline — scope above reflects what is
  realistically achievable at production-credible quality within that
  constraint, not a hypothetical larger-team scope.

## 10. Risks

| Risk | Mitigation |
|---|---|
| Severity/recommendation logic seen as a "black box" by stakeholders | Every scoring decision is built to show its own reasoning (see FR-2, FR-6) rather than return an opaque number |
| Synthetic data may not fully represent real-world edge cases | Ground-truth scenarios are defined independently before system-building, and refined when testing reveals gaps |
| Scope creep into non-essential technical features | Explicit out-of-scope list (Section 8) agreed before implementation begins |
