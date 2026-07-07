import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import EmailService
from app.core.jwt import create_access_token
from app.core.security import hash_password, verify_password
from app.repository.login_otp import LoginOTPRepository
from app.repository.user import UserRepository
from app.schema.auth import LoginChallengeResponse, LoginResponse, UserInfo


class AuthService:
    def __init__(
        self,
        user_repo: Optional[UserRepository] = None,
        login_otp_repo: Optional[LoginOTPRepository] = None,
        email_service: Optional[EmailService] = None,
    ):
        self.user_repo = user_repo or UserRepository()
        self.login_otp_repo = login_otp_repo or LoginOTPRepository()
        self.email_service = email_service or EmailService()

    def login(
        self,
        db: Session,
        email: str,
        password: str,
        otp_code: Optional[str] = None,
        otp_challenge_id: Optional[str] = None,
    ) -> Union[LoginResponse, LoginChallengeResponse]:
        """
        Authenticate user with password and enforce OTP-based second factor.

        Returns either a login challenge (OTP required) or final login response.
        """
        user = self.user_repo.get_by_email(db, email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials"
            )

        # Check if email is verified (only if REQUIRE_EMAIL_VERIFICATION is enabled)
        if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email address before logging in. Check your inbox for the verification email.",
            )

        if not verify_password(password, user.password_hash):
            if user.role != "admin":
                user.failed_login_attempts += 1
                user.last_failed_login = datetime.now(timezone.utc)

                if user.failed_login_attempts >= 3:
                    user.is_active = False
                    user.failed_login_attempts = 0
                    db.commit()
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Your account has been locked due to multiple failed login attempts. Please contact an administrator to unlock your account.",
                    )

                db.commit()
                remaining_attempts = 3 - user.failed_login_attempts
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Incorrect credentials. {remaining_attempts} attempt(s) remaining before account lock.",
                )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect credentials",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been locked. Please contact an administrator to unlock your account.",
            )

        if user.role != "admin":
            user.failed_login_attempts = 0
            user.last_failed_login = None
            db.commit()

        # Check if two-factor authentication is required
        # 2FA is required if FORCE_TWO_FACTOR_AUTH is enabled OR user has 2FA enabled
        requires_2fa = settings.FORCE_TWO_FACTOR_AUTH or user.is_two_factor_enabled
        
        if requires_2fa:
            if otp_code:
                if not otp_challenge_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="otp_challenge_id is required when submitting an OTP code.",
                    )
                return self._complete_login_with_otp(
                    db, user, otp_challenge_id, otp_code
                )

            if otp_challenge_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OTP code is required when submitting an otp_challenge_id.",
                )

            return self._initiate_login_with_otp(db, user.id, user.email, user.full_name)

        # If 2FA is not enabled, return login response directly
        return self._build_login_response(user)

    def _initiate_login_with_otp(
        self, db: Session, user_id: int, email: str, full_name: str
    ) -> LoginChallengeResponse:
        self.login_otp_repo.purge_pending_for_user(db, user_id)

        otp_length = max(1, settings.OTP_LENGTH)
        otp_code = self._generate_otp_code(otp_length)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=max(1, settings.OTP_EXPIRATION_MINUTES)
        )
        code_hash = hash_password(otp_code)

        otp_record = self.login_otp_repo.create_challenge(
            db=db, user_id=user_id, code_hash=code_hash, expires_at=expires_at
        )

        try:
            self._send_otp_email(email, otp_code, full_name)
        except Exception as exc:
            # Rollback OTP record if email delivery fails
            self.login_otp_repo.purge_pending_for_user(db, user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deliver OTP. Please try again later.",
            ) from exc

        return LoginChallengeResponse(
            status="otp_required",
            challenge_id=otp_record.id,
            expires_in=int(
                (expires_at - datetime.now(timezone.utc)).total_seconds()
            ),
            delivery_method="email",
            destination=self._mask_email(email),
            message="OTP has been sent to your email address.",
        )

    def _complete_login_with_otp(
        self,
        db: Session,
        user,
        otp_challenge_id: str,
        otp_code: str,
    ) -> LoginResponse:
        user_id = user.id
        otp_record = self.login_otp_repo.get_by_id(db, otp_challenge_id)

        if not otp_record or otp_record.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP challenge. Please request a new code.",
            )

        now = datetime.now(timezone.utc)
        if otp_record.consumed_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has already been used. Please request a new code.",
            )

        if otp_record.expires_at < now:
            self.login_otp_repo.purge_pending_for_user(db, user_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please request a new code.",
            )

        if not verify_password(otp_code, otp_record.code_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect OTP code.",
            )

        self.login_otp_repo.consume(db, otp_record)
        return self._build_login_response(user)

    def _build_login_response(self, user) -> LoginResponse:
        token = create_access_token(subject=user.email)
        user_info = UserInfo(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            phone_number=user.phone_number,
            role=user.role,
            is_active=user.is_active,
            is_email_verified=user.is_email_verified,
            is_two_factor_enabled=user.is_two_factor_enabled,
            created_at=user.created_at,
        )
        return LoginResponse(access_token=token, user=user_info)

    def _generate_otp_code(self, length: int) -> str:
        if length <= 1:
            return str(secrets.randbelow(9) + 1)
        range_start = 10 ** (length - 1)
        range_end = (10**length) - 1
        return str(secrets.randbelow(range_end - range_start + 1) + range_start)

    def _send_otp_email(
        self, recipient_email: str, otp_code: str, full_name: str
    ) -> None:
        expires_minutes = max(1, settings.OTP_EXPIRATION_MINUTES)
        subject = "OTP Kodunuz"
        body_text = (
            f"Tek seferlik giriş kodunuz: {otp_code}\n"
            f"Bu kod {expires_minutes} dakika içinde geçerlidir."
        )
        project_name = settings.PROJECT_NAME or "Uygulama"
        greeting = f"Merhaba {full_name}," if full_name else "Merhaba,"
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
        max-width: 480px;
        margin: 0 auto;
        background: #ffffff;
        border-radius: 12px;
        border: 1px solid #d9e2ec;
        box-shadow: 0 12px 24px rgba(15, 23, 42, 0.05);
        padding: 32px 28px;
        text-align: center;
      }}
      h1 {{
        font-size: 22px;
        margin-bottom: 16px;
        color: #0b7285;
      }}
      .otp {{
        display: inline-block;
        font-size: 32px;
        letter-spacing: 6px;
        font-weight: bold;
        color: #142d4c;
        background: #e0f7fa;
        border-radius: 8px;
        padding: 12px 20px;
        margin: 16px 0;
      }}
      p {{
        font-size: 15px;
        line-height: 1.6;
        margin: 12px 0;
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
      <h1>{project_name} - Tek Seferlik Giriş Kodunuz</h1>
      <p>{greeting}</p>
      <p>Aşağıdaki OTP kodunu {expires_minutes} dakika içinde kullanarak girişinizi tamamlayabilirsiniz.</p>
      <div class="otp">{otp_code}</div>
      <p>Eğer bu isteği siz göndermediyseniz lütfen hemen destek ekibimizle iletişime geçin.</p>
      <div class="footer">
        Bu e-posta otomatik olarak gönderilmiştir. Lütfen bu mesaja yanıt vermeyin.
      </div>
    </div>
  </body>
</html>
"""

        self.email_service.send_email(
            recipient_email=recipient_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )

    def _mask_email(self, email: str) -> str:
        local_part, _, domain = email.partition("@")
        if not local_part or not domain:
            return email
        if len(local_part) <= 2:
            masked_local = local_part[0] + "***"
        else:
            masked_local = f"{local_part[0]}***{local_part[-1]}"
        return f"{masked_local}@{domain}"
