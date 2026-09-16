"""Argon2id password hashing (§9.1 - memory-hard, the current OWASP
recommendation over bcrypt for new systems)."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error, InvalidHashError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """False for any hash this password does not open, including one that
    is malformed or was produced by a different algorithm.

    Catching only `VerifyMismatchError` left `InvalidHashError` to escape
    as a 500, which is both an availability bug (one corrupt `app_user`
    row breaks that account's login path) and an oracle: a 500 instead of
    a 401 distinguishes "this account exists but its hash is unreadable"
    from "wrong password", which is exactly the distinction the dummy-hash
    verification in `routers/auth.py` works to hide.
    """
    try:
        return _hasher.verify(password_hash, password)
    except (Argon2Error, InvalidHashError):
        return False
