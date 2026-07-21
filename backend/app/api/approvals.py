import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser
from app.models.approval import Approval

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("")
async def list_approvals(resource_type: str = Query(...), resource_id: str = Query(...), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Approval).where(Approval.resource_type == resource_type, Approval.resource_id == uuid.UUID(resource_id))
    )
    return [
        {"id": str(a.id), "decision": a.decision, "step_order": a.step_order, "decided_at": a.decided_at.isoformat() if a.decided_at else None}
        for a in result.scalars().all()
    ]
