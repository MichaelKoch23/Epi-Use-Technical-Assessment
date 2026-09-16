"""§9.1/§9.2: login/refresh/me and the `require_role` route dependency.

Exercised at the router-function level, like the other tests here - the
app's `get_db` dependency binds to the real configured `DATABASE_URL`, not
the ephemeral testcontainer these fixtures use (see test_hierarchy_roots.py
for the full explanation)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.passwords import hash_password
from app.core.rate_limit import RateLimiter
from app.core.security import Principal, require_role
from app.core.tokens import create_access_token, decode_token
from app.routers.auth import login, logout, me, refresh
from app.schemas.auth import LoginRequest, RefreshRequest


async def _create_user(
    db_session: AsyncSession, *, email: str, password: str, role: str
) -> uuid.UUID:
    user_id = uuid.uuid4()
    await db_session.execute(
        text(
            "INSERT INTO app_user (id, email, password_hash, role) "
            "VALUES (:id, :email, :password_hash, :role)"
        ),
        {
            "id": user_id,
            "email": email,
            "password_hash": hash_password(password),
            "role": role,
        },
    )
    await db_session.commit()
    return user_id


async def test_login_succeeds_with_correct_password(db_session: AsyncSession):
    user_id = await _create_user(
        db_session, email="a@example.com", password="correct horse", role="hr_admin"
    )

    tokens = await login(
        LoginRequest(email="a@example.com", password="correct horse"),
        session=db_session,
    )

    payload = decode_token(tokens.access_token, expected_type="access")
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "hr_admin"


async def test_login_rejects_wrong_password(db_session: AsyncSession):
    await _create_user(
        db_session, email="b@example.com", password="correct horse", role="viewer"
    )

    with pytest.raises(HTTPException) as exc_info:
        await login(
            LoginRequest(email="b@example.com", password="wrong password"),
            session=db_session,
        )
    assert exc_info.value.status_code == 401


async def test_login_rejects_unknown_email(db_session: AsyncSession):
    with pytest.raises(HTTPException) as exc_info:
        await login(
            LoginRequest(email="nobody@example.com", password="whatever"),
            session=db_session,
        )
    assert exc_info.value.status_code == 401


async def test_refresh_issues_a_new_access_token(db_session: AsyncSession):
    user_id = await _create_user(
        db_session, email="c@example.com", password="pw", role="viewer"
    )
    issued = await login(
        LoginRequest(email="c@example.com", password="pw"), session=db_session
    )

    tokens = await refresh(
        RefreshRequest(refresh_token=issued.refresh_token), session=db_session
    )

    payload = decode_token(tokens.access_token, expected_type="access")
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "viewer"
    # Rotation: the successor is a genuinely different token.
    assert tokens.refresh_token != issued.refresh_token


async def test_a_spent_refresh_token_is_rejected(db_session: AsyncSession):
    """Rotation is only meaningful if the old token stops working - without
    this, a captured token stays valid for its full seven days no matter how
    many times the real client refreshes."""
    await _create_user(
        db_session, email="spent@example.com", password="pw", role="viewer"
    )
    issued = await login(
        LoginRequest(email="spent@example.com", password="pw"), session=db_session
    )
    await refresh(
        RefreshRequest(refresh_token=issued.refresh_token), session=db_session
    )

    with pytest.raises(HTTPException) as exc_info:
        await refresh(
            RefreshRequest(refresh_token=issued.refresh_token), session=db_session
        )
    assert exc_info.value.status_code == 401


async def test_replaying_a_spent_token_revokes_the_whole_family(
    db_session: AsyncSession,
):
    """Two parties holding one token cannot be told apart, so the safe
    response to a replay is to end every live session for that user and
    make them re-authenticate."""
    await _create_user(
        db_session, email="theft@example.com", password="pw", role="viewer"
    )
    first = await login(
        LoginRequest(email="theft@example.com", password="pw"), session=db_session
    )
    second = await refresh(
        RefreshRequest(refresh_token=first.refresh_token), session=db_session
    )

    # The attacker replays the stolen (already spent) first token.
    with pytest.raises(HTTPException):
        await refresh(
            RefreshRequest(refresh_token=first.refresh_token), session=db_session
        )

    # The legitimate client's current token is now dead too.
    with pytest.raises(HTTPException) as exc_info:
        await refresh(
            RefreshRequest(refresh_token=second.refresh_token), session=db_session
        )
    assert exc_info.value.status_code == 401


async def test_logout_ends_the_session(db_session: AsyncSession):
    """Clearing the browser's copy of a token is not logging out - the
    server has to stop honouring it."""
    user_id = await _create_user(
        db_session, email="bye@example.com", password="pw", role="viewer"
    )
    issued = await login(
        LoginRequest(email="bye@example.com", password="pw"), session=db_session
    )

    await logout(
        RefreshRequest(refresh_token=issued.refresh_token),
        session=db_session,
        principal=Principal(id=user_id, role="viewer"),
    )

    with pytest.raises(HTTPException) as exc_info:
        await refresh(
            RefreshRequest(refresh_token=issued.refresh_token), session=db_session
        )
    assert exc_info.value.status_code == 401


async def test_refresh_rejects_an_access_token(db_session: AsyncSession):
    user_id = await _create_user(
        db_session, email="d@example.com", password="x", role="viewer"
    )
    access_token = create_access_token(user_id, "viewer")

    with pytest.raises(HTTPException) as exc_info:
        await refresh(RefreshRequest(refresh_token=access_token), session=db_session)
    assert exc_info.value.status_code == 401


async def test_me_reports_capabilities_by_role(db_session: AsyncSession):
    admin_id = await _create_user(
        db_session, email="e@example.com", password="x", role="hr_admin"
    )
    viewer_id = await _create_user(
        db_session, email="f@example.com", password="x", role="viewer"
    )

    admin_me = await me(
        principal=Principal(id=admin_id, role="hr_admin"), session=db_session
    )
    viewer_me = await me(
        principal=Principal(id=viewer_id, role="viewer"), session=db_session
    )

    assert admin_me.can_view_salary is True
    assert admin_me.can_edit is True
    assert viewer_me.can_view_salary is False
    assert viewer_me.can_edit is False


async def test_require_role_rejects_the_wrong_role():
    dependency = require_role("hr_admin")
    with pytest.raises(HTTPException) as exc_info:
        await dependency(principal=Principal(id=uuid.uuid4(), role="viewer"))
    assert exc_info.value.status_code == 403


async def test_require_role_allows_the_right_role():
    dependency = require_role("hr_admin")
    principal = Principal(id=uuid.uuid4(), role="hr_admin")
    assert await dependency(principal=principal) is principal


def test_rate_limiter_blocks_after_max_attempts():
    limiter = RateLimiter(max_attempts=2, window_seconds=60)
    request = SimpleNamespace(client=SimpleNamespace(host="1.2.3.4"))

    limiter(request)
    limiter(request)
    with pytest.raises(HTTPException) as exc_info:
        limiter(request)
    assert exc_info.value.status_code == 429
