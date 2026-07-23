"""Task status API — allows frontend to poll Celery task results."""
from fastapi import APIRouter, Depends
from app.deps import get_current_user, CurrentUser
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/{task_id}/status")
async def get_task_status(task_id: str, current: CurrentUser = Depends(get_current_user)):
    result = celery_app.AsyncResult(task_id)
    if result.state == "PENDING":
        return {"state": "PENDING", "result": None, "error": None}
    elif result.state == "STARTED":
        return {"state": "STARTED", "result": None, "error": None}
    elif result.state == "SUCCESS":
        return {"state": "SUCCESS", "result": result.result, "error": None}
    elif result.state == "FAILURE":
        return {"state": "FAILURE", "result": None, "error": str(result.result)}
    elif result.state == "RETRY":
        return {"state": "RETRY", "result": None, "error": None}
    return {"state": result.state, "result": None, "error": None}
