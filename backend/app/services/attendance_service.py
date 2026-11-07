from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from ..models import AttendanceSession, AttendanceRecord, Student, Class
from ..schemas.attendance_schema import SessionSummary, RecordOut

STATUS_TEXT = {
    "pending": "未点名",
    "present": "已到",
    "late": "迟到",
    "sick_leave": "已请假",
    "other": "其他",
}


def get_active_session(db: Session, class_id: int) -> Optional[AttendanceSession]:
    stmt = select(AttendanceSession).where(
        AttendanceSession.class_id == class_id,
        AttendanceSession.status == "active",
    ).order_by(AttendanceSession.id.desc())
    return db.scalars(stmt).first()


def create_session(db: Session, class_id: int) -> AttendanceSession:
    s = AttendanceSession(class_id=class_id, status="active")
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def upsert_record(
    db: Session,
    session: AttendanceSession,
    student_id: int,
    status: str,
    remark: Optional[str],
) -> AttendanceRecord:
    now = datetime.now()
    stmt = select(AttendanceRecord).where(
        AttendanceRecord.session_id == session.id,
        AttendanceRecord.student_id == student_id,
    )
    rec = db.scalars(stmt).first()
    if rec:
        rec.status = status
        rec.remark = remark if status == "other" else None
        rec.updated_at = now
    else:
        rec = AttendanceRecord(
            session_id=session.id,
            student_id=student_id,
            status=status,
            remark=remark if status == "other" else None,
        )
        db.add(rec)
    if session.started_at is None:
        session.started_at = now
    db.commit()
    db.refresh(rec)
    return rec


def finish_session(db: Session, session: AttendanceSession) -> AttendanceSession:
    session.finished_at = datetime.now()
    session.status = "finished"
    db.commit()
    db.refresh(session)
    return session


def summarize(db: Session, session: AttendanceSession) -> SessionSummary:
    records = db.scalars(select(AttendanceRecord).where(AttendanceRecord.session_id == session.id)).all()
    rec_map = {r.student_id: r for r in records}
    # 历史 session：以 records 关联的学生为准（即使后来被替换）
    # 活跃 session：以当前 active 学生为准
    if session.status == "finished" and rec_map:
        students = db.scalars(select(Student).where(Student.id.in_(rec_map.keys()))).all()
    else:
        students = db.scalars(
            select(Student).where(Student.class_id == session.class_id, Student.is_active == True)
        ).all()
    total = len(students)
    counts = {"present": 0, "late": 0, "sick_leave": 0, "other": 0, "pending": 0}
    for s in students:
        r = rec_map.get(s.id)
        st = r.status if r else "pending"
        counts[st] += 1
    return SessionSummary(
        session_id=session.id,
        started_at=session.started_at,
        finished_at=session.finished_at,
        status=session.status,
        total=total,
        present=counts["present"],
        late=counts["late"],
        sick_leave=counts["sick_leave"],
        other=counts["other"],
        pending=counts["pending"],
    )


def list_records(db: Session, session: AttendanceSession) -> List[RecordOut]:
    records = db.scalars(
        select(AttendanceRecord).where(AttendanceRecord.session_id == session.id)
    ).all()
    rec_map = {r.student_id: r for r in records}

    # 历史 session：直接从 records 关联学生（含已被替换的旧学生）
    if session.status == "finished" and rec_map:
        students = db.scalars(
            select(Student).where(Student.id.in_(rec_map.keys())).order_by(Student.student_number)
        ).all()
    else:
        # 活跃 session：当前 active 学生
        students = db.scalars(
            select(Student).where(Student.class_id == session.class_id, Student.is_active == True).order_by(Student.student_number)
        ).all()

    out: List[RecordOut] = []
    for s in students:
        r = rec_map.get(s.id)
        out.append(RecordOut(
            student_id=s.id,
            student_number=s.student_number,
            name=s.name,
            phone=s.phone,
            status=r.status if r else "pending",
            remark=r.remark if r else None,
        ))
    return out


def list_sessions(
    db: Session,
    class_id: int,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> List[AttendanceSession]:
    stmt = select(AttendanceSession).where(AttendanceSession.class_id == class_id)
    if date_from:
        stmt = stmt.where(AttendanceSession.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        stmt = stmt.where(AttendanceSession.created_at <= datetime.combine(date_to, datetime.max.time()))
    stmt = stmt.order_by(AttendanceSession.id.desc())
    return list(db.scalars(stmt).all())
