import os
from logging.config import fileConfig
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.db.base import Base
from app.models import (  # noqa: F401  (registers metadata)
    AppUser,
    AuditLog,
    AvatarImage,
    Employee,
    EmployeeAssignment,
    RefreshToken,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


_ASYNCPG_SSL_TO_LIBPQ = {"true": "require", "false": "disable"}


def _libpq_ssl_params(url: str) -> str:
    """Respell asyncpg's `ssl=` query parameter as libpq's `sslmode=`.

    The two drivers name the same setting differently, so swapping the driver
    without swapping the parameter hands psycopg an option it rejects outright
    with `invalid connection option "ssl"`.
    """
    parts = urlsplit(url)
    params = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key == "ssl":
            key = "sslmode"
            value = _ASYNCPG_SSL_TO_LIBPQ.get(value.lower(), value)
        params.append((key, value))
    return urlunsplit(parts._replace(query=urlencode(params)))


def _sync_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        from app.core.config import settings

        url = settings.DATABASE_URL

    if "+asyncpg" in url:
        return _libpq_ssl_params(
            url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
        )
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def run_migrations_offline() -> None:
    url = _sync_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _sync_database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
