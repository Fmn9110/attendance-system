from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

Status = Literal["pending", "present", "late", "sick_leave", "other"]


class RecordUpsert(BaseModel):
    student_id: int
    status: Status
    remark: Optional[str] = Field(None, max_length=255)


class RecordOut(BaseModel):
    student_id: int
    student_number: str
    name: str
    phone: Optional[str] = None
    status: Status
    remark: Optional[str] = None

    class Config:
        from_attributes = True


class SessionCreateResult(BaseModel):
    session_id: int
    started_at: Optional[datetime] = None


class SessionSummary(BaseModel):
    session_id: int
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    status: str
    total: int
    present: int
    late: int
    sick_leave: int
    other: int
    pending: int


class SessionDetail(BaseModel):
    session_id: int
    class_id: int
    class_name: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    status: str
    records: List[RecordOut]
    summary: SessionSummary


class FinishRequest(BaseModel):
    force: bool = False


class ExportSelection(BaseModel):
    session_ids: Optional[List[int]] = None
    date_from: Optional[str] = None  # YYYY-MM-DD
    date_to: Optional[str] = None
