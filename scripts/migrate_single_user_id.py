import asyncio
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session_factory

OLD = uuid.UUID("00000000-0000-0000-0000-000000000001")
NEW = uuid.UUID("16d7d4dc-d79d-412a-a4ee-b8a1f09f8276")

async def main():
    async with async_session_factory() as db:
        # Find all uuid columns
        result = await db.execute(text("""
            SELECT c.table_name, c.column_name
            FROM information_schema.columns c
            JOIN information_schema.tables t
              ON c.table_schema = t.table_schema AND c.table_name = t.table_name
            WHERE c.data_type = 'uuid' AND t.table_type = 'BASE TABLE'
            ORDER BY c.table_name, c.column_name
        """))
        rows = result.all()
        total = 0
        for table, col in rows:
            stmt = text(f"UPDATE {table} SET {col} = :new WHERE {col} = :old")
            res = await db.execute(stmt, {"new": NEW, "old": OLD})
            if res.rowcount:
                print(f"{table}.{col}: {res.rowcount} rows updated")
                total += res.rowcount
        await db.commit()
        print(f"Total rows updated: {total}")

if __name__ == "__main__":
    asyncio.run(main())
