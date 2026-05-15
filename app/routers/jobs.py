from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.dependencies import require_role
from app.models.user import User, UserRole
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/jobs", tags=["Background Jobs"])


class JobInfo(BaseModel):
    id: str
    name: str
    state: str
    result: Optional[str] = None
    traceback: Optional[str] = None
    date_done: Optional[str] = None


class QueueStats(BaseModel):
    active: int
    reserved: int
    scheduled: int
    workers: List[str]


class JobsOverview(BaseModel):
    queue_stats: QueueStats
    active_tasks: List[dict]
    scheduled_beats: List[dict]


@router.get("/status", response_model=JobsOverview)
async def jobs_overview(
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    """Get Celery queue stats: active workers, active tasks, Beat schedule."""
    try:
        inspect = celery_app.control.inspect(timeout=2.0)
        active = inspect.active() or {}
        reserved = inspect.reserved() or {}
        scheduled = inspect.scheduled() or {}
        workers = list(active.keys())

        active_tasks = []
        for worker, tasks in active.items():
            for task in (tasks or []):
                active_tasks.append({
                    "worker": worker,
                    "id": task.get("id"),
                    "name": task.get("name"),
                    "args": str(task.get("args", [])),
                })

        beat_schedule = []
        for name, conf in (celery_app.conf.beat_schedule or {}).items():
            beat_schedule.append({
                "name": name,
                "task": conf.get("task"),
                "schedule": str(conf.get("schedule")),
            })

        total_active = sum(len(t or []) for t in active.values())
        total_reserved = sum(len(t or []) for t in reserved.values())
        total_scheduled = sum(len(t or []) for t in scheduled.values())

        return JobsOverview(
            queue_stats=QueueStats(
                active=total_active,
                reserved=total_reserved,
                scheduled=total_scheduled,
                workers=workers,
            ),
            active_tasks=active_tasks,
            scheduled_beats=beat_schedule,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Could not reach Celery workers: {str(exc)}",
        )


@router.get("/{task_id}", response_model=JobInfo)
async def get_job(
    task_id: str,
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    """Get result/state for a specific Celery task by ID."""
    try:
        result = celery_app.AsyncResult(task_id)
        return JobInfo(
            id=task_id,
            name=result.name or "unknown",
            state=result.state,
            result=str(result.result) if result.result else None,
            traceback=result.traceback,
            date_done=str(result.date_done) if result.date_done else None,
        )
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Task not found: {str(exc)}")
