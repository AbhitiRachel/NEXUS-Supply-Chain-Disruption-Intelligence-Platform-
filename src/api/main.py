"""
main.py
-------
FastAPI backend for NEXUS. Deliberately thin -- every endpoint just
extracts the auth token and request body, then calls into
src/api/handlers.py, where all the real logic already lives and is
tested (see tests/test_api_handlers.py). This file cannot be run/tested
in this sandbox (no network access to install fastapi), so keeping it
thin minimizes what's actually unverified.

Run with: uvicorn src.api.main:app --reload
Requires GROQ_API_KEY set for the /query endpoint's SQL-answering path
to work end-to-end (the Graph and RAG paths work without it).

Endpoints:
  POST /auth/login          -> returns a JWT token
  POST /query                -> ask a question (any authenticated role)
  POST /whatif                -> run a what-if simulation (analyst/admin only)
  GET  /audit-log              -> view the tamper-evident audit trail (analyst/admin only)
  GET  /health
"""

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

from src.security.auth import UserStore, issue_token, AuthError
from src.agents.sql_agent import groq_sql_generator
from src.audit.hash_chain import AuditLog
from src.api.handlers import (
    handle_query, handle_whatif, handle_get_audit_log, HandlerError,
)

app = FastAPI(title="NEXUS", description="Agentic Supply Chain Resilience Platform", version="0.1.0")

# Demo user store -- replace with a real user table / identity provider
# before any real deployment. Seeded with one user per role so the API
# is immediately testable without a signup flow.
_user_store = UserStore()
_user_store.create_user("viewer_demo", "viewer123", "viewer")
_user_store.create_user("analyst_demo", "analyst123", "analyst")
_user_store.create_user("admin_demo", "admin123", "admin")

_audit_log = AuditLog()


class LoginRequest(BaseModel):
    username: str
    password: str


class QueryRequest(BaseModel):
    question: str
    entity_type: str | None = None
    entity_id: str | None = None
    duration_days: int | None = None


class WhatIfRequest(BaseModel):
    entity_type: str
    entity_id: str
    duration_days: int


def _extract_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    return authorization.removeprefix("Bearer ").strip()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/login")
def login(req: LoginRequest):
    try:
        user = _user_store.authenticate(req.username, req.password)
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return {"token": issue_token(user), "role": user.role}


@app.post("/query")
def query(req: QueryRequest, authorization: str = Header(None)):
    token = _extract_token(authorization)
    try:
        return handle_query(
            token, req.question, groq_sql_generator, _audit_log,
            entity_type=req.entity_type, entity_id=req.entity_id,
            duration_days=req.duration_days,
        )
    except HandlerError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@app.post("/whatif")
def whatif(req: WhatIfRequest, authorization: str = Header(None)):
    token = _extract_token(authorization)
    try:
        return handle_whatif(token, req.entity_type, req.entity_id, req.duration_days, _audit_log)
    except HandlerError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@app.get("/audit-log")
def audit_log(authorization: str = Header(None)):
    token = _extract_token(authorization)
    try:
        return handle_get_audit_log(token, _audit_log)
    except HandlerError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
