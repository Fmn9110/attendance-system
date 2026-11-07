from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..services.auth_service import require_class, require_matching_class
from ..services import attendance_service as svc
from ..schemas.common import ApiResponse

router = APIRouter(prefix="/api/classes/{class_id}/attendance", tags=["history"])


@router.get("/sessions", response_model=ApiResponse)
def list_sessions(
    class_id: int,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    token_class: int = Depends(require_class),
):
    require_matching_class(class_id, token_class)
    df = datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else None
    dt = datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else None
    sessions = svc.list_sessions(db, class_id, df, dt)
    items = []
    for s in sessions:
        summary = svc.summarize(db, s)
        items.append({
            "session_id": s.id,
            "started_at": s.started_at,
            "finished_at": s.finished_at,
            "status": s.status,
            "summary": summary.model_dump(),
        })
    return ApiResponse(data=items)
