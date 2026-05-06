from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.task_manager import router as task_manager_router
from app.core.config import get_allowed_origins, get_settings
from app.core.db import Base, engine
from app.models import Project, ProjectMember, Task, User


settings = get_settings()
allowed_origins = get_allowed_origins()
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.(railway\.app|up\.railway\.app|onrender\.com)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(task_manager_router, prefix="/api")
