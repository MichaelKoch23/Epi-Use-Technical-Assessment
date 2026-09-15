"""Integration test fixtures.

These tests run against a real, throwaway PostgreSQL instance (via
testcontainers), migrated with the project's actual Alembic revisions.
SQLite cannot run the recursive CTEs, partial indexes or the deferred
constraint trigger this schema depends on, so a suite that passed against
it would prove nothing about the invariants that matter (§11).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable, Coroutine, Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.community.postgres import PostgresContainer

from alembic import command
from app.models.employee import Employee
from app.services.employee_service import EmployeeService

API_DIR = Path(__file__).resolve().parent.parent

EmployeeFactory = Callable[..., Coroutine[Any, Any, Employee]]


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    with PostgresContainer("postgres:17-alpine") as container:
        yield container


@pytest.fixture(scope="session")
def _database_urls(postgres_container: PostgresContainer) -> tuple[str, str]:
    """(sync url for Alembic, async url for the app/tests)."""
    base = make_url(postgres_container.get_connection_url())
    sync_url = base.set(drivername="postgresql+psycopg").render_as_string(
        hide_password=False
    )
    async_url = base.set(drivername="postgresql+asyncpg").render_as_string(
        hide_password=False
    )
    return sync_url, async_url


@pytest.fixture(scope="session")
def _migrated(_database_urls: tuple[str, str]) -> None:
    """Run the real `alembic upgrade head` against the container — the
    same migrations `scripts/migrate.sh` runs against Neon, so a passing
    suite says something about the actual migration files too."""
    sync_url, _ = _database_urls
    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(API_DIR / "alembic"))

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("DATABASE_URL", sync_url)
    try:
        command.upgrade(config, "head")
    finally:
        monkeypatch.undo()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine(
    _database_urls: tuple[str, str], _migrated: None
) -> AsyncIterator[AsyncEngine]:
    _, async_url = _database_urls
    eng = create_async_engine(async_url)
    yield eng
    await eng.dispose()


@pytest.fixture(scope="session")
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def _clean_db(engine: AsyncEngine) -> None:
    """Every test starts from an empty schema. Real commits (including
    ones that deliberately fail at COMMIT, per the cycle-prevention
    tests) make a transaction-rollback-per-test strategy unusable here."""
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE audit_log, employee, app_user"))


@pytest_asyncio.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession], _clean_db: None
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def actor_id(db_session: AsyncSession) -> uuid.UUID:
    """A committed `app_user` row to satisfy `audit_log.actor_id`'s FK."""
    actor = uuid.uuid4()
    await db_session.execute(
        text(
            "INSERT INTO app_user (id, email, password_hash, role) "
            "VALUES (:id, :email, 'x', 'hr_admin')"
        ),
        {"id": actor, "email": f"{actor}@example.com"},
    )
    await db_session.commit()
    return actor


@pytest_asyncio.fixture
async def employee_factory(
    db_session: AsyncSession, actor_id: uuid.UUID
) -> EmployeeFactory:
    """Creates and commits an employee with sensible, unique defaults —
    override anything (`manager_id`, `salary`, ...) via keyword args."""
    service = EmployeeService(db_session)

    async def factory(
        *, manager_id: uuid.UUID | None = None, **overrides: Any
    ) -> Employee:
        suffix = uuid.uuid4().hex[:10]
        fields: dict[str, Any] = {
            "employee_number": f"E-{suffix}",
            "first_name": "Test",
            "last_name": f"Person-{suffix}",
            "email": f"{suffix}@example.com",
            "birth_date": date(1990, 1, 1),
            "position": "Engineer",
            "salary": Decimal(50000),
            "manager_id": manager_id,
            "actor_id": actor_id,
        }
        fields.update(overrides)
        employee = await service.create(**fields)
        await db_session.commit()
        return employee

    return factory
