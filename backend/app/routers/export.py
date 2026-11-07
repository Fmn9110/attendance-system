import os
import tempfile
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..database import get_db
from ..models import AttendanceSession, Class, Student, AttendanceRecord
from ..services.auth_service import require_class, require_matching_class
from ..services import attendance_service as svc
from ..services.export_naming import single_filename, batch_filename
from ..schemas.attendance_schema import ExportSelection
from ..schemas.common import ApiResponse
from ..utils.timeutil import format_duration

router = APIRouter(prefix="/api", tags=["export"])

STATUS_TEXT = {
    "pending": "未点名", "present": "已到", "late": "迟到",
    "sick_leave": "已请假", "other": "其他",
}


def _file_response(path: str, filename: str) -> FileResponse:
    from urllib.parse import quote
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)


@router.get("/attendance/{session_id}/export")
def export_single(session_id: int, db: Session = Depends(get_db), token_class: int = Depends(require_class)):
    s = db.get(AttendanceSession, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="点名场次不存在")
    require_matching_class(s.class_id, token_class)
    cls = db.get(Class, s.class_id)
    records = svc.list_records(db, s)
    rows = []
    for r in records:
        rows.append({
            "student_number": r.student_number,
            "name": r.name,
            "phone": r.phone,
            "status_text": STATUS_TEXT[r.status],
            "remark": r.remark,
        })
    filename = single_filename(cls.class_name, s.started_at)
    tmp = os.path.join(tempfile.gettempdir(), f"att_{session_id}_{int(datetime.now().timestamp())}.xlsx")
    from ..services.excel_service import export_single_session
    export_single_session(tmp, cls.class_name, s.started_at, s.finished_at, rows)
    return _file_response(tmp, filename)


@router.get("/classes/{class_id}/attendance/export")
@router.post("/classes/{class_id}/attendance/export")
def export_batch(
    class_id: int,
    db: Session = Depends(get_db),
    token_class: int = Depends(require_class),
    session_ids: str = None,
    date_from: str = None,
    date_to: str = None,
):
    require_matching_class(class_id, token_class)
    cls = db.get(Class, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")

    sid_list = []
    if session_ids:
        sid_list = [int(x) for x in session_ids.split(",") if x.strip()]
    if sid_list:
        sessions = []
        for sid in sid_list:
            s = db.get(AttendanceSession, sid)
            if s and s.class_id == class_id:
                sessions.append(s)
        if not sessions:
            raise HTTPException(status_code=400, detail="未选择有效的点名场次")
        df = min((x.started_at for x in sessions if x.started_at), default=None)
        dt = df
    else:
        df = datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else None
        dt = datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else None
        sessions = svc.list_sessions(db, class_id, df, dt)
        if not sessions:
            raise HTTPException(status_code=400, detail="所选范围内没有点名记录")
        date_from = datetime.combine(df, datetime.min.time()) if df else None
        date_to = datetime.combine(dt, datetime.max.time()) if dt else None

    # 按时间正序导出
    sessions.sort(key=lambda x: x.id)

    detail_rows = []
    summary_rows = []
    stat_map: dict[int, dict] = {}

    for idx, s in enumerate(sessions, start=1):
        records = svc.list_records(db, s)
        summary = svc.summarize(db, s)
        date_str = s.started_at.strftime("%Y-%m-%d") if s.started_at else (s.created_at.strftime("%Y-%m-%d"))
        start_str = s.started_at.strftime("%H:%M:%S") if s.started_at else ""
        end_str = s.finished_at.strftime("%H:%M:%S") if s.finished_at else ""
        dur = format_duration(s.started_at, s.finished_at)
        summary_rows.append({
            "seq": idx, "date": date_str, "started_at": start_str, "finished_at": end_str, "duration": dur,
            "total": summary.total, "present": summary.present, "late": summary.late,
            "sick_leave": summary.sick_leave, "other": summary.other, "pending": summary.pending,
        })
        for r in records:
            detail_rows.append({
                "seq": idx,
                "date": date_str, "started_at": start_str, "finished_at": end_str,
                "class_name": cls.class_name, "student_number": r.student_number,
                "name": r.name, "phone": r.phone, "status_text": STATUS_TEXT[r.status],
                "remark": r.remark,
            })
            st = stat_map.setdefault(r.student_id, {
                "student_number": r.student_number, "name": r.name,
                "total": 0, "present": 0, "late": 0, "sick_leave": 0, "other": 0,
            })
            st["total"] += 1
            if r.status in ("present", "late", "sick_leave", "other"):
                st[r.status] += 1

    # 明细按学号排序，同一学号按场次序号排序
    detail_rows.sort(key=lambda x: (x["student_number"], x["seq"]))
    student_stat_rows = sorted(stat_map.values(), key=lambda x: x["student_number"])

    filename = batch_filename(cls.class_name, date_from, date_to)
    tmp = os.path.join(tempfile.gettempdir(), f"att_batch_{class_id}_{int(datetime.now().timestamp())}.xlsx")
    from ..services.excel_service import export_batch
    export_batch(tmp, detail_rows, summary_rows, student_stat_rows)
    return _file_response(tmp, filename)
