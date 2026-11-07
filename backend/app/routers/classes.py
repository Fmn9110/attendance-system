from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..database import get_db
from ..models import Class
from ..schemas.common import ApiResponse
from ..schemas.class_schema import LoginRequest, LoginResult, ClassOut
from ..services.auth_service import authenticate, issue_token, settings
from ..utils.security import hash_password

router = APIRouter(prefix="/api/classes", tags=["classes"])


@router.get("", response_model=ApiResponse)
def list_classes(db: Session = Depends(get_db)):
    rows = db.scalars(select(Class).order_by(Class.id)).all()
    return ApiResponse(data=[ClassOut(id=c.id, class_name=c.class_name).model_dump() for c in rows])


@router.post("/login", response_model=ApiResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    cls = authenticate(db, req.class_id, req.password)
    token = issue_token(cls.id)
    return ApiResponse(data=LoginResult(
        token=token,
        class_=ClassOut(id=cls.id, class_name=cls.class_name),
        expires_days=settings.session_expire_days,
    ).model_dump())


@router.post("/change-password", response_model=ApiResponse)
def change_password(payload: dict, db: Session = Depends(get_db)):
    """修改密码：验证原始密码后设置新密码"""
    class_id = payload.get("class_id")
    old_password = payload.get("old_password", "")
    new_password = payload.get("new_password", "")
    cls = db.get(Class, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    from ..utils.security import verify_password
    if not verify_password(old_password, cls.password_hash):
        raise HTTPException(status_code=401, detail="原始密码错误")
    if len(new_password) < 4:
        raise HTTPException(status_code=400, detail="新密码至少4位")
    cls.password_hash = hash_password(new_password)
    db.commit()
    return ApiResponse(data={"ok": True})
