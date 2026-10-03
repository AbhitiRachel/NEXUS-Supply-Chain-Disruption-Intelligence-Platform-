# NEXUS — Viva & Presentation Prep Guide

---

## 1. The 30-Second Elevator Pitch (memorize this)

"NEXUS applies known techniques — knowledge graphs, retrieval, agent
orchestration — to a specific, real problem: supply chain disruption
assessment. The individual pieces aren't new. What I designed is the
integration: an analyst asks a plain question, and specialized agents
work together — tracing the disruption's reach, checking real inventory
data to separate structural risk from actual urgency, estimating dollar
impact, and recommending an action — with every step explainable rather
than a black-box score. The contribution is the design decisions, not
the underlying algorithms."

Say this BEFORE anyone asks "what's novel here" — volunteering it
upfront is stronger than being caught overclaiming and backpedaling.
See Section 7 for the full version of this answer if pressed further.

---

## 2. The Problem, In Plain English

Global supply chains are long chains of dependency: a chip factory in
Taiwan feeds an assembly plant in Japan, which makes a product sold in
Europe. When one link breaks — a port strike, a factory shutdown — the
damage doesn't just stay local. It ripples downstream, and it's hard
for a human to quickly answer "how bad is this, really, and what should
we do?"

Commercial supply-chain risk platforms already exist and address
versions of this problem at enterprise scale. NEXUS isn't claiming to
fill a gap the industry lacks — it's a self-built implementation of the
core techniques such systems rely on (graph-based dependency tracing,
document retrieval, natural-language data querying), built end-to-end
by one person to demonstrate genuine understanding of how to design and
test an agentic system, not to invent a new category of tool. Where
there's a specific design point worth defending, it's this: severity
and urgency are explicitly kept separate, using real inventory buffer
data, so a structurally severe disruption isn't automatically treated
as urgent — see the Keelung example in Section 5.

---

## 3. How It Works — Agent by Agent, Plain English

**The Supervisor (the "manager")**
Reads the question and decides which specialist(s) to call. Doesn't
follow a fixed script — it makes this decision fresh, every time, based
on what the question is actually asking.

**The Graph Agent (the "map reader")**
Understands how suppliers, ports, factories, and products connect to
each other, like a network map. Given a disruption, it traces exactly
which suppliers, factories, and products are downstream of it — and
scores how severe the situation is, showing its work (not a hidden
number).

**The RAG Agent (the "document reader")**
Searches contracts, disruption notices, and shipping reports to find
the most relevant document for a question. If the Graph agent already
knows which suppliers are affected, it tells the RAG agent — so the
document search is focused on the right entities, not guessing from the
question text alone.

**The SQL Agent (the "data analyst")**
Turns a plain question ("how many shipments were delayed?") into a
database query, runs it, and — this is the important part — if the
query fails, it reads the actual error message and rewrites the query
itself, automatically, without a human stepping in. It's also
hard-blocked from ever running anything except a read-only query, so it
can never accidentally (or maliciously) delete or change data.

**The Simulation Agent (the "what-if calculator")**
Takes a hypothetical disruption and checks real inventory data: does
the affected factory have enough buffer stock to absorb this before it
becomes a real problem? It also estimates a dollar cost at risk, based
on real historical shipment costs — not a made-up number.

**The Recommender (the "advisor")**
Turns all of that into one concrete recommendation: monitor only (if
buffer is sufficient), shift to an alternate supplier (if one already
exists), or escalate/expedite (if there's truly no backup). Every
recommendation states exactly which facts led to it.

**Security layer**
Login with roles (viewer/analyst/admin — different people get different
permissions), a filter that catches suspicious/manipulative questions
before they're processed, and a tamper-evident audit log — every action
is recorded in a way where editing any past record breaks a
cryptographic chain, making tampering detectable.

---

## 4. Key Terms You Should Be Able to Explain in Your Own Words

- **Agentic AI**: AI that doesn't just answer a question — it decides
  its own next action, uses tools, and can correct its own mistakes,
  rather than following one fixed script.
- **GraphRAG**: retrieval that uses a knowledge graph (a map of
  relationships) to answer questions that are fundamentally about
  connections — "what's downstream of X" — which plain text search
  can't do well.
- **Self-correction / ReAct loop**: the pattern of act → observe the
  result → reason about what went wrong → try again. Your SQL agent is
  the clearest example of this.
- **Hash-chained audit log**: each record stores a fingerprint of the
  record before it. Edit any past record, and the fingerprints stop
  matching — tampering becomes detectable rather than silent. (You
  chose this over blockchain deliberately — see Section 7.)
- **RBAC (role-based access control)**: different user roles get
  different permissions — a viewer can ask questions but can't run
  simulations or see the audit log; an analyst can.
- **TF-IDF**: the retrieval method your RAG agent uses right now — finds
  documents by matching important keywords. It's a legitimate, tested
  baseline; production systems typically use semantic embeddings
  instead, which you've architected room for but didn't have network
  access to install and test in your build environment.

---

## 5. Your Numbers — Cheat Sheet

- **~74 automated tests, all passing**, covering every agent, the
  security layer, and the API logic.
- **Graph agent: 5/5 ground-truth scenarios match exactly** (hand-built
  before the agent existed, to keep evaluation objective).
- **SQL self-correction: proven live** — a typo'd query fails, the
  agent reads the real error, and succeeds on the second attempt.
- **Security: proven with a real simulated attack** — direct database
  tampering was detected by the audit log; a destructive query
  ("DROP TABLE") was blocked before ever touching the database.
- **Example real output**: Keelung port, 7-day disruption → 2 suppliers,
  3 factories, 3 products affected, severity HIGH, but $145,630.57 at
  risk with a "monitor only" recommendation because factories have
  16.9+ days of buffer stock — severity and urgency are NOT the same
  thing, and your system correctly distinguishes them.

---

## 6. Suggested Live Demo Script (in order)

1. **Log in** as analyst_demo — show the role is visible on screen.
2. **Ask a Question tab**: "What is affected if Keelung port shuts
   down?" with Port/PORT-KEELUNG/7 days. Point out the severity
   breakdown is fully explained, not a mystery number.
3. **What-If Simulation tab**: same inputs. Point out severity=HIGH but
   recommendation=monitor only — explain WHY (buffer math), since this
   is your most impressive nuance.
4. **Change duration to 60 days**, rerun — show the recommendation
   flips to "shift to alternate supplier" with a named alternate. This
   demonstrates the system reasons dynamically, not from a script.
5. **SQL self-correction** (if you have this working): ask a numeric
   question, and if possible, show a deliberately broken version
   recovering. This is your strongest "is this really agentic" proof.
6. **Executive Dashboard tab**: business-level KPIs, no jargon.
7. **Audit Log tab**: show the hash chain, point out prev_hash of one
   entry matches entry_hash of the one before it.

---

## 7. Anticipated Viva Questions + Model Answers

**Q: What's new here — don't these kinds of systems already exist?**
A: "The individual components — RAG, graph traversal, text-to-SQL —
aren't novel; they're industry-standard techniques, and I want to be
upfront about that rather than overclaim. What I'd argue is new is the
integration philosophy: severity and urgency are never conflated — my
system checks real inventory buffer before deciding urgency, not just
structural risk. Agents genuinely inform each other rather than running
in parallel — my RAG agent uses the Graph agent's findings, which I
verified by finding and fixing a real bug where it didn't. Every
decision is explainable by construction, not as an afterthought. And I
built LLM-independent tests proving the self-correction behavior
actually works, rather than just asserting it. That combination,
applied to this specific problem with real empirical validation, is the
contribution — not a new algorithm."

**Q: Why didn't you use blockchain, since your original plan included it?**
A: "Blockchain and a hash-chained log provide the identical guarantee
for this use case — tamper-evidence — but blockchain requires running a
separate distributed ledger with smart contracts, which is
substantially more engineering overhead for no additional benefit here.
I made a deliberate architecture decision to use the simpler solution
that achieves the same goal, and documented that reasoning rather than
including blockchain just because it sounds more advanced."

**Q: Why TF-IDF instead of real embeddings for retrieval?**
A: "My production architecture is designed for ChromaDB with real
embeddings — the RAG agent's interface is built so that's a drop-in
swap. TF-IDF is the tested, zero-dependency baseline I built and
validated first. I found and documented a real limitation of it —
keyword frequency can outrank the semantically correct document — which
is exactly the kind of gap real embeddings are expected to close."

**Q: Is this actually 'agentic,' or just an LLM calling APIs?**
A: "Agentic requires autonomy, tool use, multi-step reasoning, and
self-correction. My Supervisor autonomously decides which agents to
call per question. My SQL agent doesn't just call a tool once — it
observes failure, reasons about the error, and retries. That loop is
the actual engineering contribution, and I tested it directly using
scripted failure scenarios, independent of any specific LLM."

**Q: How do you know your system gives correct answers?**
A: "I wrote ground-truth scenarios by hand, independently, before
building the agents — deciding what the correct answer should be
first. Then I tested the agents against those scenarios. This avoids
the trap of only checking whether the system's output looks
plausible."

**Q: What are the limitations of this system?**
A: "Three honest ones: the dataset is synthetic, appropriately scaled
for hand-verification rather than production volume; the RAG retrieval
uses a keyword-based baseline rather than semantic embeddings, due to
this build environment lacking network access to install/test that
dependency; and the routing logic in the Supervisor is rule-based
rather than LLM-based, which is a deliberate cost/speed/explainability
tradeoff, not an oversight."

**Q: What would you do with more time?**
A: "Swap in real embeddings for retrieval, add an LLM-based router for
genuinely ambiguous questions, and expand the ground-truth scenario set
before finalizing evaluation numbers."

**Q: What's the business value here?**
A: "It cuts disruption assessment from a manual, multi-system
investigation to a single question, gives a consistent severity
methodology instead of ad hoc analyst judgment, and expresses impact in
dollar terms so Operations and Finance are speaking the same language."

---

## 8. Limitations — Say These Proactively, Don't Wait to Be Asked

Bringing up known limitations yourself, before being asked, signals
maturity and self-awareness — it reads as "I understand this system
deeply enough to know its edges" rather than being caught off guard.
The same goes for novelty (Section 7's first question) — volunteer the
honest framing before anyone has to extract it from you.

1. Synthetic data, appropriately small for hand-verification.
2. TF-IDF retrieval baseline (embeddings are the designed upgrade path).
3. Rule-based routing (LLM-based routing is a natural next step for
   genuinely ambiguous questions).
4. No individual component is novel — the contribution is the
   integration philosophy and empirical rigor, not a new algorithm.

---

## 9. Why This Counts as Agentic AI, Specifically

| Property | Where it lives |
|---|---|
| Autonomy | Supervisor decides which agent(s) to call per question |
| Tool use | Agents query real graph/database/documents, not just text generation |
| Multi-step reasoning | SQL agent's retry loop; Graph agent's multi-hop traversal |
| Self-correction | SQL agent reads its own errors and retries |
| Cross-agent coordination | RAG agent uses Graph agent's findings to focus its search |
| Explainability | Every severity score and recommendation states its own reasoning |

Note: this table describes *properties*, not *inventions* — these are
recognized agentic-AI characteristics from the literature, and the
claim is that NEXUS demonstrates them, not that it invented them.
