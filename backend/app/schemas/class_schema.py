from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    class_id: int
    password: str = Field(..., min_length=1)


class ClassOut(BaseModel):
    id: int
    class_name: str

    class Config:
        from_attributes = True


class LoginResult(BaseModel):
    token: str
    class_: ClassOut
    expires_days: int
