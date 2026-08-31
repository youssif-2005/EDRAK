from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from services import auth as auth_service

router = APIRouter()


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        201: {"description": "Account created; JWT returned"},
        409: {"description": "Email already registered"},
    },
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Create an account with email/password.

    Students also get a `students` row (name defaults to the email local-part).
    Returns a JWT so the client can authenticate immediately.
    """
    return auth_service.register_user(db, payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in and receive a JWT",
    responses={
        200: {"description": "Authenticated; JWT returned"},
        401: {"description": "Invalid email or password"},
    },
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate with email and password and return a JWT."""
    return auth_service.login_user(db, payload)
