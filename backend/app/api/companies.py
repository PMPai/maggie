from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser
from app.models.project import Company
from app.schemas.project import CompanyCreate, CompanyResponse
from app.models.approval import AuditLog

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.post("", response_model=CompanyResponse)
async def create_company(req: CompanyCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    company = Company(
        code=req.code, name=req.name, company_type=req.company_type,
        tax_id=req.tax_id, address=req.address, phone=req.phone, contact_person=req.contact_person,
        created_by=current.id, updated_by=current.id,
    )
    db.add(company)
    await db.flush()
    db.add(AuditLog(
        user_id=current.id,
        action="CREATE",
        resource_type="company",
        resource_id=str(company.id),
        detail={"code": company.code, "name": company.name},
    ))
    await db.commit()
    await db.refresh(company)
    return CompanyResponse(id=str(company.id), code=company.code, name=company.name, company_type=company.company_type, tax_id=company.tax_id, status=company.status)


@router.get("", response_model=list[CompanyResponse])
async def list_companies(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Company).where(Company.deleted_at.is_(None))
        .offset((page - 1) * size).limit(size)
    )
    return [CompanyResponse(id=str(c.id), code=c.code, name=c.name, company_type=c.company_type, tax_id=c.tax_id, status=c.status) for c in result.scalars().all()]
