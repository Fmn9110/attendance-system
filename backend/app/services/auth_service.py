from datetime import timedelta
from fastapi import Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Class
from ..utils.security import verify_password

_s = URLSafeTimedSerializer(settings.secret_key, salt="attendance-class")
_bearer = HTTPBearer(auto_error=False)


def issue_token(class_id: int) -> str:
    return _s.dumps({"class_id": class_id})


def decode_token(token: str) -> int:
    max_age = settings.session_expire_days * 86400
    try:
        data = _s.loads(token, max_age=max_age)
        return int(data["class_id"])
    except SignatureExpired:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新输入密码")
    except BadSignature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的登录凭证")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的登录凭证")


def authenticate(db: Session, class_id: int, password: str) -> Class:
    cls = db.get(Class, class_id)
    if not cls or not verify_password(password, cls.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="班级密码错误")
    return cls


def require_class(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    token: str = Query(default=None),
) -> int:
    raw = None
    if credentials:
        raw = credentials.credentials
    elif token:
        raw = token
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    return decode_token(raw)


def require_matching_class(path_class_id: int, token_class_id: int) -> None:
    if path_class_id != token_class_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该班级数据")
