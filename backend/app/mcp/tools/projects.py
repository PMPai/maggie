"""MCP tools for project CRUD."""
from uuid import UUID


def register_project_tools(mcp):
    from app.db.session import async_session_factory
    from app.models.project import Project
    from sqlalchemy import select

    @mcp.tool()
    async def list_projects() -> list[dict]:
        """List all projects."""
        async with async_session_factory() as db:
            result = await db.execute(
                select(Project).where(Project.deleted_at.is_(None)).order_by(Project.created_at.desc())
            )
            return [
                {
                    "id": str(p.id),
                    "code": p.internal_project_code,
                    "name": p.project_name,
                    "status": p.status,
                    "currency": p.currency,
                }
                for p in result.scalars().all()
            ]

    @mcp.tool()
    async def get_project(project_id: str) -> dict | None:
        """Get a single project by ID."""
        async with async_session_factory() as db:
            result = await db.execute(select(Project).where(Project.id == UUID(project_id)))
            p = result.scalar_one_or_none()
            if not p:
                return None
            return {
                "id": str(p.id),
                "code": p.internal_project_code,
                "name": p.project_name,
                "description": p.description,
                "status": p.status,
                "currency": p.currency,
                "start_date": str(p.start_date) if p.start_date else None,
                "planned_end_date": str(p.planned_end_date) if p.planned_end_date else None,
            }

    @mcp.tool()
    async def create_project(code: str, name: str, currency: str = "TWD") -> dict:
        """Create a new project."""
        async with async_session_factory() as db:
            p = Project(
                internal_project_code=code,
                project_name=name,
                currency=currency,
                status="ACTIVE",
            )
            db.add(p)
            await db.commit()
            await db.refresh(p)
            return {"id": str(p.id), "code": p.internal_project_code, "name": p.project_name}
