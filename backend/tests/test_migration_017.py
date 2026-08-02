"""Migration 017 adds documents.ocr_text column (nullable).

Exercises the actual migration module's upgrade()/downgrade() functions
via an alembic op context, instead of simulating the change with raw SQL.
"""
import importlib.util
from contextlib import contextmanager
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text

MIGRATION_PATH = Path(__file__).resolve().parent.parent / "alembic" / "versions" / "017_ocr_text.py"


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("migration_017_ocr_text", MIGRATION_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@contextmanager
def _alembic_op_context(sync_conn):
    """Bind alembic.op to a real Operations context for the duration of the block."""
    mc = MigrationContext.configure(sync_conn)
    with Operations.context(mc):
        yield


def _run_migration(sync_conn, direction):
    """Invoke the actual migration upgrade()/downgrade() under an alembic op context."""
    mod = _load_migration_module()
    with _alembic_op_context(sync_conn):
        if direction == "up":
            mod.upgrade()
        else:
            mod.downgrade()


async def _reset_schema(test_engine):
    async with test_engine.begin() as conn:
        await conn.exec_driver_sql("DROP SCHEMA public CASCADE")
        await conn.exec_driver_sql("CREATE SCHEMA public")
        from app.db.base import Base
        await conn.run_sync(Base.metadata.create_all)


@pytest.mark.asyncio
async def test_migration_017_upgrade_adds_nullable_ocr_text(test_engine):
    """upgrade() adds ocr_text (nullable) to documents."""
    await _reset_schema(test_engine)

    # Simulate pre-017 schema: drop the column the model already declares.
    async with test_engine.begin() as conn:
        await conn.execute(text("ALTER TABLE documents DROP COLUMN ocr_text"))

    # Apply the actual migration upgrade().
    async with test_engine.begin() as conn:
        await conn.run_sync(_run_migration, "up")

    def _inspect(sync_conn):
        return {c["name"]: c for c in inspect(sync_conn).get_columns("documents")}

    async with test_engine.connect() as conn:
        cols = await conn.run_sync(_inspect)

    assert "ocr_text" in cols
    assert cols["ocr_text"]["nullable"] is True


@pytest.mark.asyncio
async def test_migration_017_downgrade_removes_ocr_text(test_engine):
    """downgrade() drops ocr_text from documents."""
    await _reset_schema(test_engine)

    # Start from post-017 state (column present from create_all); downgrade removes it.
    async with test_engine.begin() as conn:
        await conn.run_sync(_run_migration, "down")

    def _inspect(sync_conn):
        return [c["name"] for c in inspect(sync_conn).get_columns("documents")]

    async with test_engine.connect() as conn:
        cols = await conn.run_sync(_inspect)

    assert "ocr_text" not in cols
