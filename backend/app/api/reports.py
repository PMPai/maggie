from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _rows(result):
    columns = result.keys()
    return [dict(zip(columns, row)) for row in result.all()]


@router.get("/contract-item-balances")
async def contract_item_balances(contract_id: str | None = None, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = "SELECT * FROM v_contract_item_balances"
    if contract_id:
        query += " WHERE contract_id = :cid"
        result = await db.execute(text(query), {"cid": contract_id})
    else:
        result = await db.execute(text(query))
    return _rows(result)


@router.get("/project-summary")
async def project_summary(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM v_project_commercial_summary"))
    return _rows(result)


@router.get("/retention-balances")
async def retention_balances(contract_id: str | None = None, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = "SELECT * FROM v_retention_balances"
    if contract_id:
        query += " WHERE contract_id = :cid"
        result = await db.execute(text(query), {"cid": contract_id})
    else:
        result = await db.execute(text(query))
    return _rows(result)


@router.get("/uninvoiced")
async def uninvoiced(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM v_uninvoiced_approved_amounts"))
    return _rows(result)


@router.get("/invoice-outstanding")
async def invoice_outstanding(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM v_invoice_outstanding"))
    return _rows(result)


@router.get("/collection-variances")
async def collection_variances(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM v_collection_variances"))
    return _rows(result)


@router.get("/cost-margin")
async def cost_margin(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM v_cost_margin_analysis"))
    return _rows(result)


@router.get("/pending-exceptions")
async def pending_exceptions(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM v_pending_exceptions"))
    return _rows(result)


@router.get("/audit-log")
async def audit_log(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 100"))
    return _rows(result)
