from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectResponse
from app.models.approval import AuditLog

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse)
async def create_project(req: ProjectCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    project = Project(
        internal_project_code=req.internal_project_code, project_name=req.project_name,
        description=req.description, start_date=req.start_date, planned_end_date=req.planned_end_date,
        currency=req.currency, default_tax_rate=req.default_tax_rate,
        special_fund_description=req.special_fund_description,
        created_by=current.id, updated_by=current.id,
    )
    db.add(project)
    await db.flush()
    db.add(AuditLog(
        user_id=current.id,
        action="CREATE",
        resource_type="project",
        resource_id=str(project.id),
        detail={"project_code": req.internal_project_code, "project_name": req.project_name},
    ))
    await db.commit()
    await db.refresh(project)
    return ProjectResponse(id=str(project.id), internal_project_code=project.internal_project_code, project_name=project.project_name, description=project.description, status=project.status, currency=project.currency, default_tax_rate=project.default_tax_rate, special_fund_description=project.special_fund_description)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project).where(Project.deleted_at.is_(None))
        .offset((page - 1) * size).limit(size)
    )
    return [ProjectResponse(id=str(p.id), internal_project_code=p.internal_project_code, project_name=p.project_name, description=p.description, status=p.status, currency=p.currency, default_tax_rate=p.default_tax_rate, special_fund_description=p.special_fund_description) for p in result.scalars().all()]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pid = __import__("uuid").UUID(project_id)
    result = await db.execute(select(Project).where(Project.id == pid, Project.deleted_at.is_(None)))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(id=str(p.id), internal_project_code=p.internal_project_code, project_name=p.project_name, description=p.description, status=p.status, currency=p.currency, default_tax_rate=p.default_tax_rate, special_fund_description=p.special_fund_description)