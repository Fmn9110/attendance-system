import os
import time
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..database import get_db
from ..models import Class, Student
from ..schemas.common import ApiResponse
from ..schemas.student_schema import PreviewResult, ConfirmImportResult
from ..services.auth_service import require_class, require_matching_class
from ..services import excel_service
from ..config import settings

router = APIRouter(prefix="/api/classes/{class_id}/students", tags=["students"])


def _check(class_id: int, token_class: int, db: Session) -> Class:
    require_matching_class(class_id, token_class)
    cls = db.get(Class, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    return cls


@router.get("", response_model=ApiResponse)
def list_students(class_id: int, db: Session = Depends(get_db), token_class: int = Depends(require_class)):
    _check(class_id, token_class, db)
    rows = db.scalars(
        select(Student)
        .where(Student.class_id == class_id, Student.is_active == True)
        .order_by(Student.student_number)
    ).all()
    return ApiResponse(data=[
        {"id": s.id, "student_number": s.student_number, "name": s.name, "phone": s.phone}
        for s in rows
    ])


@router.post("/import/preview", response_model=ApiResponse)
async def preview_import(
    class_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    token_class: int = Depends(require_class),
):
    _check(class_id, token_class, db)
    data = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"文件超过 {settings.max_upload_mb}MB")
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ("xlsx", "xls", "xlsm"):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx / .xls 文件")
    try:
        result = excel_service.parse_roster(data, file.filename or "roster.xlsx")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Excel 解析失败：{e}")
    if result.missing_columns:
        raise HTTPException(status_code=400, detail=f"Excel 缺少必要列：{', '.join(result.missing_columns)}")
    # 临时保存到 uploads，供 confirm 使用
    os.makedirs(settings.upload_dir, exist_ok=True)
    safe_name = f"preview_{class_id}_{int(time.time())}_{os.path.basename(file.filename or 'roster.xlsx')}"
    path = os.path.join(settings.upload_dir, safe_name)
    with open(path, "wb") as f:
        f.write(data)
    return ApiResponse(data={"preview": result.model_dump(), "stored_path": path})


@router.post("/import/confirm", response_model=ApiResponse)
def confirm_import(
    class_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    token_class: int = Depends(require_class),
):
    cls = _check(class_id, token_class, db)
    path = payload.get("stored_path")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=400, detail="预览文件不存在，请重新上传")
    # 安全校验：路径必须在 upload_dir 目录内，防止路径遍历攻击
    upload_dir_abs = os.path.abspath(settings.upload_dir)
    path_abs = os.path.abspath(path)
    if not path_abs.startswith(upload_dir_abs + os.sep):
        raise HTTPException(status_code=400, detail="非法的文件路径")
    with open(path_abs, "rb") as f:
        data = f.read()
    result = excel_service.parse_roster(data, path)
    if result.missing_columns:
        raise HTTPException(status_code=400, detail=f"Excel 缺少必要列：{', '.join(result.missing_columns)}")
    valid_rows = [r for r in result.rows if not r.errors]
    if not valid_rows:
        raise HTTPException(status_code=400, detail="没有可导入的有效学生数据")

    # 旧学生置为 inactive（保留历史关联）
    old = db.scalars(select(Student).where(Student.class_id == class_id, Student.is_active == True)).all()
    deactivated = 0
    for s in old:
        s.is_active = False
        deactivated += 1

    # 查询所有该班级的学生（包括 inactive），用于更新而不是重复插入
    existing = db.scalars(select(Student).where(Student.class_id == class_id)).all()
    existing_map = {s.student_number: s for s in existing}

    imported = 0
    updated = 0
    for r in valid_rows:
        if r.student_number in existing_map:
            # 更新已有学生
            s = existing_map[r.student_number]
            s.name = r.name
            s.phone = r.phone
            s.is_active = True
            updated += 1
        else:
            # 新增学生
            db.add(Student(
                class_id=class_id,
                student_number=r.student_number,
                name=r.name,
                phone=r.phone,
                is_active=True,
            ))
            imported += 1
    db.commit()
    try:
        os.remove(path)
    except OSError:
        pass
    return ApiResponse(data=ConfirmImportResult(imported=imported, deactivated=deactivated).model_dump())


@router.get("/template")
def download_template(
    class_id: int,
    db: Session = Depends(get_db),
    token_class: int = Depends(require_class),
):
    from fastapi.responses import FileResponse
    from openpyxl import Workbook
    _check(class_id, token_class, db)
    # 生成模板文件
    wb = Workbook()
    ws = wb.active
    ws.title = "花名册"
    ws.append(["学号", "姓名", "电话"])
    ws.append(["20261114001", "张三", "13800138000"])
    ws.append(["20261114002", "李四", ""])
    # 设置列宽
    ws.column_dimensions['A'].width = 16
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 16
    # 临时保存
    template_path = os.path.join(settings.upload_dir, "roster_template.xlsx")
    os.makedirs(settings.upload_dir, exist_ok=True)
    wb.save(template_path)
    return FileResponse(template_path, filename="花名册导入模板.xlsx")
