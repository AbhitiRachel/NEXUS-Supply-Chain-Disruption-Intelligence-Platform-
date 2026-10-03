"""
auth.py
-------
Basic authentication and role-based access control (RBAC).

Password hashing uses Python's built-in PBKDF2 (hashlib.pbkdf2_hmac) --
not bcrypt -- because bcrypt isn't installable without network access in
this build environment. PBKDF2 with a high iteration count is a
legitimate, still-recommended (NIST SP 800-132) password hashing choice;
this is a documented substitution, not a security shortcut.

Roles (simplest useful set for this system):
  - viewer: can query the dashboard, cannot see raw audit log details
  - analyst: can query + view audit log + trigger simulations
  - admin: analyst + can manage other users
"""

import hashlib
import hmac
import os
import time
from dataclasses import dataclass

import jwt

SECRET_KEY = os.environ.get("NEXUS_JWT_SECRET", "dev-only-secret-change-in-production")
TOKEN_EXPIRY_SECONDS = 8 * 60 * 60  # 8-hour session

ROLES = ["viewer", "analyst", "admin"]
ROLE_PERMISSIONS = {
    "viewer": {"query"},
    "analyst": {"query", "view_audit_log", "run_simulation"},
    "admin": {"query", "view_audit_log", "run_simulation", "manage_users"},
}

PBKDF2_ITERATIONS = 260_000  # OWASP-recommended minimum as of recent guidance


@dataclass
class User:
    username: str
    role: str
    password_hash: str
    salt: str


class AuthError(Exception):
    pass


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or os.urandom(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return derived.hex(), salt.hex()


def verify_password(password: str, password_hash: str, salt_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    derived, _ = hash_password(password, salt)
    return hmac.compare_digest(derived, password_hash)


class UserStore:
    """In-memory user store for the demo/dev build. Swap for a real table
    (or a managed identity provider) for a production deployment."""

    def __init__(self):
        self._users: dict[str, User] = {}

    def create_user(self, username: str, password: str, role: str) -> User:
        if role not in ROLES:
            raise ValueError(f"Unknown role: {role}. Must be one of {ROLES}")
        if username in self._users:
            raise ValueError(f"User already exists: {username}")
        password_hash, salt = hash_password(password)
        user = User(username=username, role=role, password_hash=password_hash, salt=salt)
        self._users[username] = user
        return user

    def get(self, username: str) -> User | None:
        return self._users.get(username)

    def authenticate(self, username: str, password: str) -> User:
        user = self._users.get(username)
        if not user or not verify_password(password, user.password_hash, user.salt):
            raise AuthError("Invalid username or password")
        return user


def issue_token(user: User) -> str:
    payload = {
        "sub": user.username,
        "role": user.role,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRY_SECONDS,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired")
    except jwt.InvalidTokenError:
        raise AuthError("Invalid token")


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())


def require_permission(token: str, permission: str) -> dict:
    """Verifies the token AND checks the role has the required permission.
    Raises AuthError if either check fails -- use this at every protected
    endpoint rather than checking the two separately."""
    claims = verify_token(token)
    if not has_permission(claims["role"], permission):
        raise AuthError(f"Role '{claims['role']}' lacks permission '{permission}'")
    return claims
