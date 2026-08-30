"""MCP tools for collection (收款单) CRUD."""
from uuid import UUID


def register_collection_tools(mcp):
    from app.db.session import async_session_factory
    from app.models.collection import Collection, CollectionStatus
    from sqlalchemy import select
    from datetime import date

    @mcp.tool()
    async def list_collections(project_id: str, status: str | None = None) -> list[dict]:
        """List collections for a project, optionally filtered by status."""
        async with async_session_factory() as db:
            q = select(Collection).where(
                Collection.project_id == UUID(project_id), Collection.deleted_at.is_(None)
            )
            if status:
                q = q.where(Collection.status == CollectionStatus(status))
            result = await db.execute(q)
            return [
                {
                    "id": str(c.id),
                    "receipt_no": c.receipt_no,
                    "receipt_date": str(c.receipt_date) if c.receipt_date else None,
                    "amount": float(c.amount_received),
                    "status": c.status.value,
                }
                for c in result.scalars().all()
            ]

    @mcp.tool()
    async def create_collection(project_id: str, contract_id: str, receipt_no: str,
                                  amount: float, receipt_date: str | None = None) -> dict:
        """Create a collection record (收款单)."""
        async with async_session_factory() as db:
            col = Collection(
                project_id=UUID(project_id), contract_id=UUID(contract_id),
                receipt_no=receipt_no,
                receipt_date=date.fromisoformat(receipt_date) if receipt_date else None,
                amount_received=amount,
                status=CollectionStatus.PLANNED,
            )
            db.add(col)
            await db.commit()
            await db.refresh(col)
            return {"id": str(col.id), "status": col.status.value}

    @mcp.tool()
    async def confirm_collection(collection_id: str) -> dict:
        """Confirm a PLANNED collection (PLANNED → CONFIRMED)."""
        async with async_session_factory() as db:
            result = await db.execute(select(Collection).where(Collection.id == UUID(collection_id)))
            col = result.scalar_one_or_none()
            if not col:
                return {"error": "Not found"}
            col.status = CollectionStatus.CONFIRMED
            await db.commit()
            return {"id": str(col.id), "status": col.status.value}

    @mcp.tool()
    async def receive_collection(collection_id: str) -> dict:
        """Mark a CONFIRMED collection as RECEIVED (money arrived)."""
        async with async_session_factory() as db:
            result = await db.execute(select(Collection).where(Collection.id == UUID(collection_id)))
            col = result.scalar_one_or_none()
            if not col:
                return {"error": "Not found"}
            col.status = CollectionStatus.RECEIVED
            col.receipt_date = date.today()
            await db.commit()
            return {"id": str(col.id), "status": col.status.value}
