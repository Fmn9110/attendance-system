from typing import List, Optional
from pydantic import BaseModel


class StudentOut(BaseModel):
    id: int
    student_number: str
    name: str
    phone: Optional[str] = None

    class Config:
        from_attributes = True


class PreviewRow(BaseModel):
    row_index: int          # Excel 行号（从 1 开始，含表头）
    student_number: str
    name: str
    phone: Optional[str] = None
    errors: List[str] = []


class PreviewResult(BaseModel):
    total_rows: int
    valid_count: int
    error_count: int
    rows: List[PreviewRow]
    missing_columns: List[str] = []


class ConfirmImportResult(BaseModel):
    imported: int
    deactivated: int
