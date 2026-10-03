"""
sql_agent.py
------------
SQL Agent: turns a plain-language question into a SQL query, runs it,
and self-corrects if the query fails -- reads the database error,
feeds it back, and tries again, up to a capped number of attempts.

Design choice worth noting in the report: SQL GENERATION (needs an LLM)
and SELF-CORRECTION CONTROL FLOW (detect failure -> feed back error ->
retry -> cap attempts) are deliberately separated. The generator is a
pluggable function; the control flow around it is plain Python. This
means the self-correction LOGIC itself -- the actual engineering
contribution -- is fully unit-testable without needing a live LLM at
all, by substituting a fake generator that deliberately fails then
recovers. The real Groq-backed generator (groq_sql_generator) is wired
in for production use once GROQ_API_KEY is set.

Safety guard: every generated query is checked before execution and
REJECTED if it isn't a read-only SELECT statement. This means even a
manipulated question, a prompt-injection attempt, or a confused LLM
output can never modify or delete data -- this agent can only ever read.
"""

import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "nexus.db"
MAX_ATTEMPTS = 3

# Keywords that, if found anywhere in a generated query, cause it to be
# rejected outright before ever touching the database.
FORBIDDEN_KEYWORDS = [
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "ATTACH", "DETACH",
    "PRAGMA", "VACUUM", "REPLACE", "CREATE", "TRUNCATE",
]


class UnsafeQueryError(Exception):
    """Raised when a generated query isn't a safe, read-only SELECT."""


@dataclass
class SQLAttempt:
    sql: str
    success: bool
    error: str | None = None
    rejected_unsafe: bool = False


@dataclass
class SQLAnswerResult:
    question: str
    final_sql: str | None
    rows: list
    columns: list
    attempts: list = field(default_factory=list)
    succeeded: bool = False

    @property
    def attempts_used(self) -> int:
        return len(self.attempts)

    @property
    def was_self_corrected(self) -> bool:
        """True if it failed at least once before eventually succeeding."""
        return self.succeeded and self.attempts_used > 1


def get_schema_description(db_path: Path = DB_PATH) -> str:
    """
    Introspects the actual SQLite schema (not hand-typed) so the prompt
    given to the LLM always matches the real database -- if a column gets
    renamed later, this description updates automatically.
    """
    conn = sqlite3.connect(db_path)
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()

    lines = []
    for (table_name,) in tables:
        cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        col_desc = ", ".join(f"{c[1]} ({c[2]})" for c in cols)
        lines.append(f"{table_name}: {col_desc}")

    conn.close()
    return "\n".join(lines)


def _is_safe_select(sql: str) -> bool:
    stripped = sql.strip().rstrip(";").strip()
    if not re.match(r"(?is)^\s*select\b", stripped):
        return False
    upper = stripped.upper()
    return not any(kw in upper for kw in FORBIDDEN_KEYWORDS)


def _execute(sql: str, db_path: Path = DB_PATH) -> tuple[list, list]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(sql)
        rows = [dict(r) for r in cursor.fetchall()]
        columns = [d[0] for d in cursor.description] if cursor.description else []
        return rows, columns
    finally:
        conn.close()


def answer_question(
    question: str,
    generate_sql_fn,
    db_path: Path = DB_PATH,
    max_attempts: int = MAX_ATTEMPTS,
) -> SQLAnswerResult:
    """
    Core self-correction loop, independent of which LLM (or fake, for
    testing) generates the SQL.

    generate_sql_fn signature: (question: str, schema: str, error_feedback: str | None) -> str
    Called with error_feedback=None on the first attempt, then with the
    previous attempt's SQL + error message on each retry.
    """
    schema = get_schema_description(db_path)
    attempts: list[SQLAttempt] = []
    error_feedback = None

    for attempt_num in range(1, max_attempts + 1):
        sql = generate_sql_fn(question, schema, error_feedback)

        if not _is_safe_select(sql):
            attempts.append(SQLAttempt(sql=sql, success=False, rejected_unsafe=True))
            error_feedback = (
                f"Your previous query was REJECTED for safety: only read-only "
                f"SELECT statements are allowed. You wrote: {sql}"
            )
            continue

        try:
            rows, columns = _execute(sql, db_path)
            attempts.append(SQLAttempt(sql=sql, success=True))
            return SQLAnswerResult(
                question=question,
                final_sql=sql,
                rows=rows,
                columns=columns,
                attempts=attempts,
                succeeded=True,
            )
        except sqlite3.Error as e:
            attempts.append(SQLAttempt(sql=sql, success=False, error=str(e)))
            error_feedback = f"Your previous query failed with this error: {e}\nQuery was: {sql}"

    # Exhausted all attempts without success
    return SQLAnswerResult(
        question=question,
        final_sql=None,
        rows=[],
        columns=[],
        attempts=attempts,
        succeeded=False,
    )


def groq_sql_generator(question: str, schema: str, error_feedback: str | None = None) -> str:
    """
    Production SQL generator using Groq's free tier. Requires GROQ_API_KEY.
    Not runnable in this sandbox (no network access) -- the self-correction
    loop above is tested independently using fake generators; this is the
    real generator to wire in once you have an API key.
    """
    import os

    try:
        from groq import Groq
    except ImportError:
        raise RuntimeError("Run: pip install groq")

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set. Get a free key at https://console.groq.com")

    client = Groq(api_key=api_key)

    system_prompt = f"""You translate plain-language questions into SQLite SELECT queries.

Schema:
{schema}

Rules:
- Output ONLY the SQL query, nothing else -- no explanation, no markdown fences.
- Only SELECT statements are allowed. Never write DROP/DELETE/UPDATE/INSERT/ALTER.
- Use exact column and table names from the schema above."""

    user_content = question
    if error_feedback:
        user_content = f"{question}\n\n{error_feedback}\nPlease provide a corrected query."

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    sql = response.choices[0].message.content.strip()
    # Strip markdown fences if the model added them despite instructions
    sql = re.sub(r"^```(?:sql)?\s*|\s*```$", "", sql, flags=re.MULTILINE).strip()
    return sql
