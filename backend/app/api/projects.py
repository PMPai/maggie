from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser
from app.models.project import Project, ProjectMember
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectMemberAdd, ProjectMemberResponse
from app.models.identity import UserRoleEnum

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse)
async def create_project(req: ProjectCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    project = Project(
        organization_id=current.organization_id,
        internal_project_code=req.internal_project_code, project_name=req.project_name,
        description=req.description, start_date=req.start_date, planned_end_date=req.planned_end_date,
        currency=req.currency, default_tax_rate=req.default_tax_rate,
        created_by=current.user.id, updated_by=current.user.id,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return ProjectResponse(id=str(project.id), internal_project_code=project.internal_project_code, project_name=project.project_name, description=project.description, status=project.status, currency=project.currency, default_tax_rate=project.default_tax_rate)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import or_
    if UserRoleEnum.SYSTEM_ADMIN in current.roles:
        result = await db.execute(
            select(Project).where(Project.organization_id == current.organization_id, Project.deleted_at.is_(None))
            .offset((page - 1) * size).limit(size)
        )
    else:
        result = await db.execute(
            select(Project).join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == current.user.id, ProjectMember.status == "ACTIVE", Project.deleted_at.is_(None))
            .offset((page - 1) * size).limit(size)
        )
    return [ProjectResponse(id=str(p.id), internal_project_code=p.internal_project_code, project_name=p.project_name, description=p.description, status=p.status, currency=p.currency, default_tax_rate=p.default_tax_rate) for p in result.scalars().all()]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.auth.rbac import require_project_member
    pid = __import__("uuid").UUID(project_id)
    await require_project_member(pid, current, db)
    result = await db.execute(select(Project).where(Project.id == pid, Project.deleted_at.is_(None)))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(id=str(p.id), internal_project_code=p.internal_project_code, project_name=p.project_name, description=p.description, status=p.status, currency=p.currency, default_tax_rate=p.default_tax_rate)


@router.post("/{project_id}/members", response_model=ProjectMemberResponse)
async def add_member(project_id: str, req: ProjectMemberAdd, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    import uuid as _uuid
    pid = _uuid.UUID(project_id)
    member = ProjectMember(project_id=pid, user_id=_uuid.UUID(req.user_id), project_role=req.project_role, created_by=current.user.id, updated_by=current.user.id)
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return ProjectMemberResponse(id=str(member.id), user_id=str(member.user_id), project_role=member.project_role, status=member.status)
