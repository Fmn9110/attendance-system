"""重置某班级密码。
用法：
    cd backend
    python -m scripts.set_password.py 计科2601班 newpassword
"""
import sys
from sqlalchemy import select
from app.database import SessionLocal
from app.models import Class
from app.utils.security import hash_password


def main():
    if len(sys.argv) != 3:
        print("用法：python -m scripts.set_password.py <班级名> <新密码>")
        sys.exit(1)
    name, pwd = sys.argv[1], sys.argv[2]
    db = SessionLocal()
    try:
        c = db.scalars(select(Class).where(Class.class_name == name)).first()
        if not c:
            print(f"未找到班级：{name}")
            sys.exit(1)
        c.password_hash = hash_password(pwd)
        db.commit()
        print(f"已更新 {name} 的密码")
    finally:
        db.close()


if __name__ == "__main__":
    main()
