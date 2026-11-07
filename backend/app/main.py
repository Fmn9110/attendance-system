import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .config import settings, BASE_DIR
from .database import Base, engine
from . import models  # noqa: F401  ensure models are imported for metadata
from .routers import classes, students, attendance, history, export

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(os.path.dirname(settings.database_url.split("///")[-1]), exist_ok=True) if settings.database_url.startswith("sqlite") else None
    Base.metadata.create_all(bind=engine)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    if settings.debug:
        return JSONResponse(status_code=500, content={"code": 500, "message": str(exc), "data": None})
    return JSONResponse(status_code=500, content={"code": 500, "message": "服务器内部错误", "data": None})


app.include_router(classes.router)
app.include_router(students.router)
app.include_router(attendance.router)
app.include_router(history.router)
app.include_router(export.router)


@app.get("/api/health")
def health():
    return {"code": 0, "message": "ok", "data": {"status": "up"}}


# 前端静态文件
frontend_dir = BASE_DIR.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
