from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr

from app.core.config import settings


class LoginInput(BaseModel):
    email: EmailStr
    password: str
    otp_code: Optional[str] = None
    otp_challenge_id: Optional[str] = None


class RegisterInput(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone_number: str


class UserInfo(BaseModel):
    """User information in login response (without sensitive data)"""
    id: int
    email: str
    full_name: str
    phone_number: str
    role: str
    is_active: bool
    is_email_verified: bool
    is_two_factor_enabled: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Login response with token and user info"""
    status: Literal["authenticated"] = "authenticated"
    access_token: str
    token_type: str = "bearer"
    expires_in: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES or 1440
    user: UserInfo


class LoginChallengeResponse(BaseModel):
    """Response returned when OTP verification is required"""
    status: Literal["otp_required"] = "otp_required"
    challenge_id: str
    expires_in: int
    delivery_method: Literal["email"] = "email"
    destination: str
    message: str


class RegisterResponse(BaseModel):
    """Registration response"""
    status: Literal["success"] = "success"
    message: str
    user_id: int
    email: str


class EmailVerificationResponse(BaseModel):
    """Email verification response"""
    status: Literal["success"] = "success"
    message: str


class ForgotPasswordInput(BaseModel):
    """Request password reset"""
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Password reset request response"""
    status: Literal["success"] = "success"
    message: str


class ResetPasswordInput(BaseModel):
    """Reset password with token"""
    token: str
    new_password: str


class ResetPasswordResponse(BaseModel):
    """Password reset response"""
    status: Literal["success"] = "success"
    message: str


# Backward compatibility alias
Token = LoginResponse
