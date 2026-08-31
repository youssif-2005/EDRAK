from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Payload for creating a new account."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: str = Field(default="student", pattern="^(student|teacher|admin)$")
    name: str | None = Field(default=None, max_length=100)
    grade: str | None = Field(default=None, max_length=50)


class LoginRequest(BaseModel):
    """Payload for exchanging credentials for a JWT."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Public user fields returned after auth."""

    id: int
    email: EmailStr
    role: str
    student_id: int | None = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """JWT plus the authenticated user."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
