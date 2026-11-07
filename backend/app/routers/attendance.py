from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AttendanceSession, Student, AttendanceRecord
from ..schemas.common import ApiResponse
from ..schemas.attendance_schema import RecordUpsert, FinishRequest, SessionCreateResult
from ..services.auth_service import require_class, require_matching_class
from ..services import attendance_service as svc
from ..utils.security import verify_password

router = APIRouter(prefix="/api", tags=["attendance"])


def _load_session(db: Session, session_id: int, token_class: int) -> AttendanceSession:
    s = db.get(AttendanceSession, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="点名场次不存在")
    require_matching_class(s.class_id, token_class)
    return s


@router.get("/classes/{class_id}/attendance/active", response_model=ApiResponse)
def get_active(class_id: int, db: Session = Depends(get_db), token_class: int = Depends(require_class)):
    require_matching_class(class_id, token_class)
    s = svc.get_active_session(db, class_id)
    if not s:
        return ApiResponse(data=None)
    summary = svc.summarize(db, s)
    return ApiResponse(data={"session_id": s.id, "started_at": s.started_at, "summary": summary.model_dump()})


@router.post("/classes/{class_id}/attendance/sessions", response_model=ApiResponse)
def new_session(class_id: int, db: Session = Depends(get_db), token_class: int = Depends(require_class)):
    require_matching_class(class_id, token_class)
    # 如果已有 active session，直接返回，避免重复
    existing = svc.get_active_session(db, class_id)
    if existing:
        return ApiResponse(data=SessionCreateResult(session_id=existing.id, started_at=existing.started_at).model_dump())
    s = svc.create_session(db, class_id)
    return ApiResponse(data=SessionCreateResult(session_id=s.id, started_at=s.started_at).model_dump())


@router.post("/attendance/{session_id}/record", response_model=ApiResponse)
def upsert_record(
    session_id: int,
    payload: RecordUpsert,
    db: Session = Depends(get_db),
    token_class: int = Depends(require_class),
):
    s = _load_session(db, session_id, token_class)
    student = db.get(Student, payload.student_id)
    if not student or student.class_id != s.class_id:
        raise HTTPException(status_code=400, detail="学生不存在")
    rec = svc.upsert_record(db, s, payload.student_id, payload.status, payload.remark)
    summary = svc.summarize(db, s)
    return ApiResponse(data={
        "record": {"student_id": rec.student_id, "status": rec.status, "remark": rec.remark},
        "session": {"started_at": s.started_at, "status": s.status},
        "summary": summary.model_dump(),
    })


@router.post("/attendance/{session_id}/finish", response_model=ApiResponse)
def finish(
    session_id: int,
    payload: FinishRequest = FinishRequest(),
    db: Session = Depends(get_db),
    token_class: int = Depends(require_class),
):
    s = _load_session(db, session_id, token_class)
    if s.status == "finished":
        raise HTTPException(status_code=400, detail="本次点名已结束")
    summary = svc.summarize(db, s)
    if summary.pending > 0 and not payload.force:
        # 未强制结束：返回提示，前端让班长选择
        return ApiResponse(code=1001, message=f"还有 {summary.pending} 名学生未完成", data={"summary": summary.model_dump()})
    s = svc.finish_session(db, s)
    summary = svc.summarize(db, s)
    return ApiResponse(data={"summary": summary.model_dump()})


@router.get("/attendance/{session_id}", response_model=ApiResponse)
def session_detail(session_id: int, db: Session = Depends(get_db), token_class: int = Depends(require_class)):
    s = _load_session(db, session_id, token_class)
    from ..models import Class
    cls = db.get(Class, s.class_id)
    records = svc.list_records(db, s)
    summary = svc.summarize(db, s)
    return ApiResponse(data={
        "session_id": s.id,
        "class_id": s.class_id,
        "class_name": cls.class_name,
        "started_at": s.started_at,
        "finished_at": s.finished_at,
        "status": s.status,
        "records": [r.model_dump() for r in records],
        "summary": summary.model_dump(),
    })


@router.delete("/attendance/{session_id}", response_model=ApiResponse)
def delete_session(
    session_id: int,
    payload: dict = None,
    db: Session = Depends(get_db),
    token_class: int = Depends(require_class),
):
    """删除单条点名记录，需要密码验证"""
    s = _load_session(db, session_id, token_class)
    if not payload or not payload.get("password"):
        raise HTTPException(status_code=400, detail="请输入班级密码")
    # 验证密码
    from ..models import Class
    cls = db.get(Class, s.class_id)
    if not verify_password(payload["password"], cls.password_hash):
        raise HTTPException(status_code=401, detail="密码错误")
    # 删除关联的记录和场次
    db.query(AttendanceRecord).filter(AttendanceRecord.session_id == session_id).delete()
    db.delete(s)
    db.commit()
    return ApiResponse(data={"ok": True})
