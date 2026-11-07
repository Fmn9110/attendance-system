from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from ..database.base import Base


class Class(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    class_name = Column(String(64), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    students = relationship("Student", back_populates="class_", cascade="all, delete-orphan")
    sessions = relationship("AttendanceSession", back_populates="class_", cascade="all, delete-orphan")
