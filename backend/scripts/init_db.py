"""初始化数据库并创建默认 5 个班级。
用法：
    cd backend
    python -m scripts.init_db
"""
from sqlalchemy import select
from app.database import Base, engine, SessionLocal
from app.models import Class
from app.utils.security import hash_password

DEFAULT_CLASSES = [
    ("计科2601班", "123456"),
    ("计科2602班", "123456"),
    ("计科2603班", "123456"),
    ("计科2604班", "123456"),
    ("计科2605班", "123456"),
]


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for name, pwd in DEFAULT_CLASSES:
            existing = db.scalars(select(Class).where(Class.class_name == name)).first()
            if existing:
                print(f"[skip] {name} 已存在 (id={existing.id})")
                continue
            c = Class(class_name=name, password_hash=hash_password(pwd))
            db.add(c)
            print(f"[add] {name} 初始密码：{pwd}")
        db.commit()
        print("\n初始化完成。请登录后尽快通过 set_password.py 修改默认密码。")
    finally:
        db.close()


if __name__ == "__main__":
    main()
