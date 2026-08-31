from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload

from config import settings
from database import get_db
from models import Student, User
from schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse

ALLOWED_ROLES = {"student", "teacher", "admin"}
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(*, user_id: int, email: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _user_response(user: User) -> UserResponse:
    student_id = user.student.id if user.student is not None else None
    return UserResponse(id=user.id, email=user.email, role=user.role, student_id=student_id)


def register_user(db: Session, payload: RegisterRequest) -> TokenResponse:
    role = payload.role.lower()
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid role")

    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=role,
    )
    db.add(user)
    db.flush()

    if role == "student":
        name = payload.name or payload.email.split("@")[0]
        db.add(Student(user_id=user.id, name=name, grade=payload.grade, xp=0, streak=0))

    db.commit()
    user = (
        db.query(User)
        .options(joinedload(User.student))
        .filter(User.id == user.id)
        .one()
    )

    token = create_access_token(user_id=user.id, email=user.email, role=user.role)
    return TokenResponse(access_token=token, user=_user_response(user))


def login_user(db: Session, payload: LoginRequest) -> TokenResponse:
    user = (
        db.query(User)
        .options(joinedload(User.student))
        .filter(User.email == payload.email.lower())
        .first()
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user_id=user.id, email=user.email, role=user.role)
    return TokenResponse(access_token=token, user=_user_response(user))


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode the Bearer JWT and load the corresponding user. Used by later-day routes."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
