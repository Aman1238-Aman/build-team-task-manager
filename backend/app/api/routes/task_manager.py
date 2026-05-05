from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import and_, select
from sqlalchemy.orm import Session, joinedload

from app.core.db import get_db
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.models.task_manager import Project, ProjectMember, ProjectRole, Task, TaskStatus, User, UserRole
from app.schemas.task_manager import (
    AuthResponse,
    DashboardOut,
    LoginRequest,
    MemberAdd,
    MemberOut,
    ProjectCreate,
    ProjectOut,
    SignupRequest,
    TaskCreate,
    TaskOut,
    TaskUpdate,
    UserBase,
)

router = APIRouter()
bearer = HTTPBearer(auto_error=False)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = db.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def project_query_for(user: User):
    base = select(Project).options(joinedload(Project.members).joinedload(ProjectMember.user))
    if user.role == UserRole.admin:
        return base
    return base.join(ProjectMember).where(ProjectMember.user_id == user.id)


def get_project_for_user(project_id: int, user: User, db: Session) -> Project:
    project = db.execute(project_query_for(user).where(Project.id == project_id)).unique().scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def membership_for(project: Project, user_id: int) -> ProjectMember | None:
    return next((member for member in project.members if member.user_id == user_id), None)


def ensure_project_admin(project: Project, user: User) -> None:
    member = membership_for(project, user.id)
    if user.role != UserRole.admin and (member is None or member.role != ProjectRole.admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


def ensure_assignee_in_project(project: Project, assignee_id: int | None) -> None:
    if assignee_id is not None and not any(member.user_id == assignee_id for member in project.members):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignee must be a project member")


@router.post("/auth/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> AuthResponse:
    exists = db.scalar(select(User).where(User.email == payload.email))
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        name=payload.name.strip(),
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return AuthResponse(access_token=create_access_token(str(user.id)), user=user)


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return AuthResponse(access_token=create_access_token(str(user.id)), user=user)


@router.get("/auth/me", response_model=UserBase)
def me(user: User = Depends(current_user)) -> User:
    return user


@router.get("/users", response_model=list[UserBase])
def users(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[User]:
    if user.role == UserRole.admin:
        return list(db.scalars(select(User).order_by(User.name)).all())
    project_ids = select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
    visible_user_ids = select(ProjectMember.user_id).where(ProjectMember.project_id.in_(project_ids))
    return list(db.scalars(select(User).where(User.id.in_(visible_user_ids)).order_by(User.name)).all())


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)) -> DashboardOut:
    tasks = []
    projects = []
    now = datetime.now(timezone.utc)

    by_status = {task_status.value: 0 for task_status in TaskStatus}
    overdue = 0

    for task in tasks:
        by_status[task.status.value] += 1
        if task.due_date and task.status != TaskStatus.done:
            due_date = task.due_date if task.due_date.tzinfo else task.due_date.replace(tzinfo=timezone.utc)
            overdue += int(due_date < now)

    return DashboardOut(
        total_projects=len(projects),
        total_tasks=len(tasks),
        assigned_to_me=0,
        overdue=overdue,
        by_status=by_status,
        tasks=tasks[:12],
    )
