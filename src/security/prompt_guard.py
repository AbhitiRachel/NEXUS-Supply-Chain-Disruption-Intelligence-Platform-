"""
prompt_guard.py
------------------
First-line defense against prompt injection in user-facing questions,
BEFORE they ever reach an LLM or the Supervisor's routing logic.

This is deliberately layered with, not a replacement for, the SQL
agent's own SELECT-only execution guard (src/agents/sql_agent.py) --
defense in depth. Even if a malicious input somehow got past this
screen, the SQL agent's execution-time guard would still block a
destructive query from ever running. This module catches manipulation
attempts EARLIER and logs them, so they're visible to an analyst rather
than silently absorbed.

Detection is pattern-based and intentionally conservative: it flags
COMMON injection phrasings (ignore previous instructions, reveal your
system prompt, act as..., etc.) without trying to be a comprehensive
classifier -- a determined attacker could still phrase around this.
The report should be explicit that this is a first line of defense,
not a complete solution, and that the execution-layer guard (reject
non-SELECT SQL) is the layer that actually matters for data safety.
"""

import re
from dataclasses import dataclass

INJECTION_PATTERNS = [
    r"ignore (all |previous |prior )*instructions",
    r"disregard (all |previous |prior )*instructions",
    r"reveal (your |the )?(system )?prompt",
    r"you are now",
    r"act as (a|an) (?!analyst|assistant\b)",  # "act as X" flagged unless benign role
    r"new instructions?:",
    r"forget (everything|all previous)",
    r"override (your |the )?(rules|guidelines|instructions)",
    r"pretend (you are|to be)",
    r"jailbreak",
    r"do anything now",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


@dataclass
class GuardResult:
    is_safe: bool
    matched_pattern: str | None = None
    original_question: str = ""


def screen_input(question: str) -> GuardResult:
    """
    Returns a GuardResult flagging whether the input shows signs of a
    prompt-injection attempt. Callers should log flagged inputs to the
    audit log (see src/audit/hash_chain.py) and can choose to block or
    proceed-with-caution depending on the deployment's risk tolerance.
    """
    for pattern in COMPILED_PATTERNS:
        match = pattern.search(question)
        if match:
            return GuardResult(is_safe=False, matched_pattern=match.group(0), original_question=question)

    return GuardResult(is_safe=True, original_question=question)
