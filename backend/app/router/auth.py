from fastapi import APIRouter, Depends, Request, HTTPException, status, Query
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Union
from app.schema.auth import (
    LoginChallengeResponse,
    LoginInput,
    LoginResponse,
    RegisterInput,
    RegisterResponse,
    EmailVerificationResponse,
    ForgotPasswordInput,
    ForgotPasswordResponse,
    ResetPasswordInput,
    ResetPasswordResponse,
)
from app.db.session import get_db
from app.service.deps import (
    get_auth_service,
    get_user_service,
    get_email_verification_service,
    get_password_reset_service,
)
from app.service.auth import AuthService
from app.service.user import UserService
from app.service.email_verification import EmailVerificationService
from app.service.password_reset import PasswordResetService
from app.repository.user import UserRepository
from app.core.email import EmailService
from app.core.config import settings
from app.core.validation import validate_password

router = APIRouter(prefix="/v1/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=201,
)
@limiter.limit("5/minute")
def register(
    request: Request,
    payload: RegisterInput,
    db: Session = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
):
    """
    Register a new user.
    
    After registration, user must verify their email before they can login.
    Rate limit: 5 requests per minute per IP address.
    """
    # Create user (email will not be verified)
    new_user = user_service.create_user(
        db=db,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        role="customer",  # Default role for new registrations
        is_active=True,
    )

    # Create email verification token
    email_verification_service = get_email_verification_service()
    verification_token = email_verification_service.create_verification_token(
        db=db, user_id=new_user.id
    )
    
    # Send verification email
    try:
        _send_verification_email(payload.email, payload.full_name, verification_token)
    except Exception as e:
        # If email fails, still return success but log the error
        print(f"Failed to send verification email: {e}")

    return RegisterResponse(
        status="success",
        message="Registration successful. Please check your email to verify your account.",
        user_id=new_user.id,
        email=new_user.email,
    )


@router.post(
    "/verify-email",
    response_model=EmailVerificationResponse,
)
def verify_email(
    token: str = Query(..., description="Email verification token"),
    db: Session = Depends(get_db),
    email_verification_service: EmailVerificationService = Depends(get_email_verification_service),
):
    """
    Verify user's email address using verification token.
    
    This endpoint validates the token, marks it as used, and verifies the user's email.
    """
    try:
        user_id = email_verification_service.verify_token(db=db, token=token)
        return EmailVerificationResponse(
            status="success",
            message="Email verified successfully. You can now log in.",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during email verification: {str(e)}",
        )


@router.post(
    "/login",
    response_model=Union[LoginResponse, LoginChallengeResponse],
    responses={
        200: {"description": "Login successful or OTP challenge issued"},
        400: {"description": "Invalid OTP submission"},
        401: {"description": "Invalid credentials"},
        403: {"description": "Account locked or email not verified"},
    },
)
@limiter.limit("5/minute")
def login(
    request: Request,
    payload: LoginInput,
    db: Session = Depends(get_db),
    auth_svc: AuthService = Depends(get_auth_service),
):
    """
    Login with email and password.
    
    Rate limit: 5 requests per minute per IP address.

    Returns either an OTP challenge (if 2FA is enabled) or JWT token after successful verification.
    Email must be verified before login.
    """
    return auth_svc.login(
        db=db,
        email=payload.email,
        password=payload.password,
        otp_code=payload.otp_code,
        otp_challenge_id=payload.otp_challenge_id,
    )


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
)
@limiter.limit("5/minute")
def forgot_password(
    request: Request,
    payload: ForgotPasswordInput,
    db: Session = Depends(get_db),
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
):
    """
    Request a password reset.
    
    If the email exists, a reset token will be sent to the user's email.
    For security reasons, the response is always the same regardless of whether
    the email exists or not.
    
    Rate limit: 5 requests per minute per IP address.
    """
    # Create reset token (returns None if user doesn't exist)
    reset_token = password_reset_service.create_reset_token(db=db, email=payload.email)

    # Only send email if token was created (user exists)
    if reset_token:
        # Get user info for email
        user_repo = UserRepository()
        user = user_repo.get_by_email(db, payload.email)
        
        if user:
            try:
                _send_password_reset_email(
                    email=payload.email,
                    full_name=user.full_name,
                    token=reset_token,
                )
            except Exception as e:
                # Log error but don't expose it to user
                print(f"Failed to send password reset email: {e}")

    # Always return success to prevent email enumeration
    return ForgotPasswordResponse(
        status="success",
        message="If an account with that email exists, a password reset link has been sent.",
    )


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
)
def reset_password(
    payload: ResetPasswordInput,
    db: Session = Depends(get_db),
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
):
    """
    Reset password using a reset token.
    
    This endpoint validates the token and sets a new password for the user.
    """
    # Validate password strength
    is_valid, error_msg = validate_password(payload.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )

    try:
        user_id = password_reset_service.reset_password(
            db=db,
            token=payload.token,
            new_password=payload.new_password,
        )
        return ResetPasswordResponse(
            status="success",
            message="Password has been reset successfully. You can now log in with your new password.",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during password reset: {str(e)}",
        )


def _send_verification_email(email: str, full_name: str, token: str) -> None:
    """Send email verification email"""
    email_service = EmailService()
    
    verification_url = f"{settings.BASE_URL}/v1/auth/verify-email?token={token}"
    project_name = settings.PROJECT_NAME or "Application"
    greeting = f"Hello {full_name}," if full_name else "Hello,"
    
    subject = "Verify Your Email Address"
    body_text = (
        f"{greeting}\n\n"
        f"Thank you for registering with {project_name}.\n\n"
        f"Please click the following link to verify your email address:\n"
        f"{verification_url}\n\n"
        f"This link will expire in 24 hours.\n\n"
        f"If you did not create an account, please ignore this email."
    )
    
    body_html = f"""\
<html>
  <head>
    <meta charset="utf-8" />
    <style>
      body {{
        background-color: #f7f9fc;
        font-family: Arial, sans-serif;
        color: #1f2933;
        padding: 24px;
      }}
      .container {{
        max-width: 600px;
        margin: 0 auto;
        background: #ffffff;
        border-radius: 12px;
        border: 1px solid #d9e2ec;
        box-shadow: 0 12px 24px rgba(15, 23, 42, 0.05);
        padding: 32px 28px;
      }}
      h1 {{
        font-size: 24px;
        margin-bottom: 16px;
        color: #0b7285;
      }}
      p {{
        font-size: 15px;
        line-height: 1.6;
        margin: 12px 0;
      }}
      .button {{
        display: inline-block;
        background-color: #0b7285;
        color: #ffffff;
        padding: 12px 24px;
        text-decoration: none;
        border-radius: 6px;
        margin: 16px 0;
      }}
      .footer {{
        margin-top: 24px;
        font-size: 12px;
        color: #617d98;
      }}
    </style>
  </head>
  <body>
    <div class="container">
      <h1>{project_name} - Verify Your Email</h1>
      <p>{greeting}</p>
      <p>Thank you for registering with {project_name}.</p>
      <p>Please click the button below to verify your email address:</p>
      <a href="{verification_url}" class="button">Verify Email</a>
      <p>Or copy and paste this link into your browser:</p>
      <p style="word-break: break-all; color: #0b7285;">{verification_url}</p>
      <p>This link will expire in 24 hours.</p>
      <p>If you did not create an account, please ignore this email.</p>
      <div class="footer">
        This email was sent automatically. Please do not reply to this message.
      </div>
    </div>
  </body>
</html>
"""

    email_service.send_email(
        recipient_email=email,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
    )


def _send_password_reset_email(email: str, full_name: str, token: str) -> None:
    """Send password reset email"""
    email_service = EmailService()
    
    reset_url = f"{settings.BASE_URL}/v1/auth/reset-password?token={token}"
    project_name = settings.PROJECT_NAME or "Application"
    greeting = f"Hello {full_name}," if full_name else "Hello,"
    
    subject = "Reset Your Password"
    body_text = (
        f"{greeting}\n\n"
        f"You requested a password reset for your {project_name} account.\n\n"
        f"Please click the following link to reset your password:\n"
        f"{reset_url}\n\n"
        f"This link will expire in {settings.PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES} minutes.\n\n"
        f"If you did not request a password reset, please ignore this email and your password will remain unchanged."
    )
    
    body_html = f"""\
<html>
  <head>
    <meta charset="utf-8" />
    <style>
      body {{
        background-color: #f7f9fc;
        font-family: Arial, sans-serif;
        color: #1f2933;
        padding: 24px;
      }}
      .container {{
        max-width: 600px;
        margin: 0 auto;
        background: #ffffff;
        border-radius: 12px;
        border: 1px solid #d9e2ec;
        box-shadow: 0 12px 24px rgba(15, 23, 42, 0.05);
        padding: 32px 28px;
      }}
      h1 {{
        font-size: 24px;
        margin-bottom: 16px;
        color: #0b7285;
      }}
      p {{
        font-size: 15px;
        line-height: 1.6;
        margin: 12px 0;
      }}
      .button {{
        display: inline-block;
        background-color: #0b7285;
        color: #ffffff;
        padding: 12px 24px;
        text-decoration: none;
        border-radius: 6px;
        margin: 16px 0;
      }}
      .warning {{
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 6px;
        padding: 12px;
        margin: 16px 0;
        color: #856404;
      }}
      .footer {{
        margin-top: 24px;
        font-size: 12px;
        color: #617d98;
      }}
    </style>
  </head>
  <body>
    <div class="container">
      <h1>{project_name} - Reset Your Password</h1>
      <p>{greeting}</p>
      <p>You requested a password reset for your {project_name} account.</p>
      <p>Please click the button below to reset your password:</p>
      <a href="{reset_url}" class="button">Reset Password</a>
      <p>Or copy and paste this link into your browser:</p>
      <p style="word-break: break-all; color: #0b7285;">{reset_url}</p>
      <p>This link will expire in {settings.PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES} minutes.</p>
      <div class="warning">
        <strong>Security Notice:</strong> If you did not request a password reset, please ignore this email and your password will remain unchanged.
      </div>
      <div class="footer">
        This email was sent automatically. Please do not reply to this message.
      </div>
    </div>
  </body>
</html>
"""

    email_service.send_email(
        recipient_email=email,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
    )
