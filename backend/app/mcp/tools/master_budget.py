"""MCP tools for master budget queries."""
from uuid import UUID


def register_master_budget_tools(mcp):
    from app.db.session import async_session_factory
    from app.models.contract import Contract, ContractVersion, ContractItem
    from app.models.collection import Collection, CollectionAllocation, CollectionStatus
    from sqlalchemy import select
    from datetime import date

    @mcp.tool()
    async def get_master_budget(project_id: str) -> dict:
        """Get the master budget for a project — per-item budget, margin, collection tracking."""
        async with async_session_factory() as db:
            pid = UUID(project_id)
            contracts = await db.execute(
                select(Contract).where(Contract.project_id == pid, Contract.deleted_at.is_(None))
            )
            items_out = []
            for contract in contracts.scalars().all():
                if not contract.active_version_id:
                    continue
                items = await db.execute(
                    select(ContractItem).where(
                        ContractItem.contract_version_id == contract.active_version_id,
                        ContractItem.is_heading == False,
                    )
                )
                for item in items.scalars().all():
                    line_amount = float(item.line_amount or 0)
                    unit_cost = float(item.unit_cost or 0)
                    margin = (float(item.unit_price or 0) - unit_cost) * float(item.contract_quantity or 0)
                    margin_pct = (margin / line_amount * 100) if line_amount else 0
                    overdue = (item.expected_payment_date and
                               item.expected_payment_date < date.today() and
                               line_amount > 0)
                    items_out.append({
                        "contract_id": str(contract.id),
                        "item_id": str(item.id),
                        "name": item.source_description,
                        "quantity": float(item.contract_quantity or 0),
                        "unit_price": float(item.unit_price or 0),
                        "unit_cost": unit_cost,
                        "line_amount": line_amount,
                        "margin": margin,
                        "margin_pct": round(margin_pct, 1),
                        "payment_date": str(item.expected_payment_date) if item.expected_payment_date else None,
                        "overdue": overdue,
                    })
            return {"project_id": project_id, "items": items_out}
