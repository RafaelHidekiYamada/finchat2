"""Execução das migrations utilizando a mesma configuração da API."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, event, pool

from app.core.config import get_settings
from app.db.base import Base
from app import models


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
database_url = get_settings().database_url


def render_type(kind, value, _autogen_context):
    """Congela o tipo monetário também em futuras revisões autogeradas."""
    if kind == "type" and isinstance(value, models.Money):
        return 'sa.Numeric(14, 2).with_variant(sa.BigInteger(), "sqlite")'
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=database_url.startswith("sqlite"),
        render_item=render_type,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(database_url, poolclass=pool.NullPool)
    if connectable.dialect.name == "sqlite":
        @event.listens_for(connectable, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=connection.dialect.name == "sqlite",
            render_item=render_type,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
