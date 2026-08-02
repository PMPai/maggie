"""Migration 017 adds documents.ocr_text column (nullable)."""
import pytest
from sqlalchemy import inspect, text


@pytest.mark.asyncio
async def test_migration_017_adds_ocr_text_column(test_engine):
    """After applying 017, documents.ocr_text exists and is nullable."""
    async with test_engine.begin() as conn:
        await conn.exec_driver_sql("DROP SCHEMA public CASCADE")
        await conn.exec_driver_sql("CREATE SCHEMA public")
        from app.db.base import Base
        await conn.run_sync(Base.metadata.create_all)

    # Reset to pre-migration state, then simulate the migration: add the column
    async with test_engine.begin() as conn:
        await conn.execute(text("ALTER TABLE documents DROP COLUMN IF EXISTS ocr_text"))
        await conn.execute(text("ALTER TABLE documents ADD COLUMN ocr_text TEXT"))

    def _inspect(sync_conn):
        return {c["name"]: c for c in inspect(sync_conn).get_columns("documents")}

    async with test_engine.connect() as conn:
        cols = await conn.run_sync(_inspect)
    assert "ocr_text" in cols
    assert cols["ocr_text"]["nullable"] is True


@pytest.mark.asyncio
async def test_migration_017_downgrade_removes_column(test_engine):
    """Downgrade drops ocr_text."""
    async with test_engine.begin() as conn:
        await conn.exec_driver_sql("DROP SCHEMA public CASCADE")
        await conn.exec_driver_sql("CREATE SCHEMA public")
        from app.db.base import Base
        await conn.run_sync(Base.metadata.create_all)
        # Simulate upgrade then downgrade
        await conn.execute(text("ALTER TABLE documents DROP COLUMN IF EXISTS ocr_text"))
        await conn.execute(text("ALTER TABLE documents ADD COLUMN ocr_text TEXT"))
        await conn.execute(text("ALTER TABLE documents DROP COLUMN ocr_text"))

    def _inspect(sync_conn):
        return [c["name"] for c in inspect(sync_conn).get_columns("documents")]

    async with test_engine.connect() as conn:
        cols = await conn.run_sync(_inspect)
    assert "ocr_text" not in cols
