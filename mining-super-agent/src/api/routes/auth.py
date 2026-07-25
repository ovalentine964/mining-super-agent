"""
Authentication routes — JWT with refresh tokens and MFA.

Security features:
- TOTP-based MFA (Google Authenticator compatible)
- QR code generation for MFA setup
- 10 backup codes (bcrypt hashed) for MFA recovery
- MFA-required login flow with lockout
- MFA disable endpoint (requires current TOTP code)
- Account lockout after 5 failed attempts (15 min)
- Rate limiting on all auth endpoints (via Caddy)
"""

from __future__ import annotations

import hashlib
import io
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.db.database import get_db_session
from src.db.models import User

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)
bearer_scheme = HTTPBearer(auto_error=False)

# MFA configuration
MFA_ISSUER = getattr(settings, "mfa_issuer_name", None) or "Mining Super-Agent"
BACKUP_CODE_COUNT = 10
TOTP_VALID_WINDOW = 1  # Allow 1 step drift (30 seconds)


# ── Request / Response Models ────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = None
    phone: str | None = None
    preferred_language: str = Field(default="en")

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username must be alphanumeric")
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Must contain uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Must contain lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Must contain digit")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = None
    backup_code: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900
    mfa_required: bool = False


class MFASetupResponse(BaseModel):
    secret: str
    otpauth_url: str
    qr_code_url: str
    backup_codes: list[str]


class MFADisableRequest(BaseModel):
    totp_code: str = Field(..., min_length=6, max_length=6)


class MFAVerifyRequest(BaseModel):
    totp_code: str = Field(..., min_length=6, max_length=6)


# ── Token Helpers ────────────────────────────────────────────────

def _create_access_token(user_id: int, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.jwt_secret_key.get_secret_value(), algorithm=settings.jwt_algorithm)


def _create_refresh_token(user_id: int) -> tuple[str, str, datetime]:
    token = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    return token, token_hash, expires_at


async def _get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


# ── MFA Helpers ──────────────────────────────────────────────────

def _generate_backup_codes() -> tuple[list[str], list[str]]:
    """Generate backup codes and their bcrypt hashes.

    Returns:
        (plaintext_codes, bcrypt_hashes) — store hashes in DB, return plaintext to user.
    """
    codes = [secrets.token_urlsafe(8).upper()[:8] for _ in range(BACKUP_CODE_COUNT)]
    hashes = [pwd_context.hash(code) for code in codes]
    return codes, hashes


def _verify_backup_code(code: str, backup_hashes: list[str]) -> tuple[bool, int]:
    """Verify a backup code against stored hashes.

    Returns:
        (is_valid, index_of_matched_hash) or (False, -1)
    """
    for i, stored_hash in enumerate(backup_hashes):
        if pwd_context.verify(code.upper(), stored_hash):
            return True, i
    return False, -1


def _generate_qr_code_svg(otpauth_url: str) -> str:
    """Generate a QR code as SVG (no external image library needed)."""
    try:
        import qrcode
        import qrcode.image.svg

        factory = qrcode.image.svg.SvgPathImage
        img = qrcode.make(otpauth_url, image_factory=factory)
        buffer = io.BytesIO()
        img.save(buffer)
        return buffer.getvalue().decode("utf-8")
    except ImportError:
        # Fallback: return a text-based representation
        return f"<!-- QR code generation requires 'qrcode' package -->\n<!-- Manual entry URL: {otpauth_url} -->"


# ── Routes ───────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db_session)):
    """Register a new user account."""
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    existing = await db.execute(select(User).where(User.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already taken")

    user = User(
        email=req.email,
        username=req.username,
        hashed_password=pwd_context.hash(req.password),
        full_name=req.full_name,
        phone=req.phone,
        preferred_language=req.preferred_language,
    )
    db.add(user)
    await db.flush()

    access_token = _create_access_token(user.id, user.email)
    refresh_token, _, _ = _create_refresh_token(user.id)

    logger.info("New user registered: %s (id=%s)", user.email, user.id)

    return {
        "user_id": user.id,
        "username": user.username,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 900,
    }


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    """Authenticate user and return tokens.

    If MFA is enabled:
    - Returns 428 with mfa_required=true if no TOTP/backup code provided
    - Validates TOTP code or backup code
    - On backup code use, removes used code from stored hashes
    """
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if user is None or not pwd_context.verify(req.password, user.hashed_password):
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
                logger.warning("Account locked: %s after %d failed attempts", user.email, user.failed_login_attempts)
            await db.flush()
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        remaining = (user.locked_until - datetime.now(timezone.utc)).seconds // 60
        raise HTTPException(
            status_code=423,
            detail=f"Account temporarily locked. Try again in {remaining} minutes.",
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    # ── MFA Check ────────────────────────────────────────────────
    if user.mfa_enabled:
        mfa_verified = False

        # Try TOTP code
        if req.totp_code:
            try:
                import pyotp
                totp = pyotp.TOTP(user.mfa_secret)
                if totp.verify(req.totp_code, valid_window=TOTP_VALID_WINDOW):
                    mfa_verified = True
                    logger.info("MFA TOTP verified for user %s", user.email)
            except ImportError:
                logger.error("pyotp not installed — cannot verify MFA")
                raise HTTPException(status_code=500, detail="MFA verification unavailable")

        # Try backup code
        if not mfa_verified and req.backup_code:
            if user.mfa_backup_codes:
                is_valid, code_index = _verify_backup_code(req.backup_code, user.mfa_backup_codes)
                if is_valid:
                    mfa_verified = True
                    # Remove used backup code (single-use)
                    user.mfa_backup_codes.pop(code_index)
                    await db.flush()
                    remaining = len(user.mfa_backup_codes)
                    logger.info(
                        "MFA backup code used for user %s (%d remaining)",
                        user.email,
                        remaining,
                    )
                    if remaining <= 2:
                        logger.warning(
                            "User %s has only %d backup codes remaining!",
                            user.email,
                            remaining,
                        )

        if not mfa_verified:
            # No valid MFA code provided
            return TokenResponse(
                access_token="",
                refresh_token="",
                expires_in=0,
                mfa_required=True,
            )

    # ── Login Success ────────────────────────────────────────────
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)
    user.last_login_ip = request.client.host if request.client else None
    await db.flush()

    access_token = _create_access_token(user.id, user.email)
    refresh_token, _, _ = _create_refresh_token(user.id)

    logger.info("User logged in: %s (MFA=%s)", user.email, user.mfa_enabled)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        mfa_required=False,
    )


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def mfa_setup(
    user: Annotated[User, Depends(_get_current_user)],
    db: AsyncSession = Depends(get_db_session),
):
    """Set up TOTP-based MFA for the authenticated user.

    Returns:
    - TOTP secret (for manual entry)
    - otpauth:// URL (for QR code generation)
    - QR code URL (SVG endpoint)
    - 10 backup codes (SAVE THESE — shown only once, bcrypt-hashed in DB)
    """
    if user.mfa_enabled:
        raise HTTPException(status_code=409, detail="MFA already enabled. Disable first.")

    try:
        import pyotp
    except ImportError:
        raise HTTPException(status_code=501, detail="pyotp not installed — MFA unavailable")

    # Generate TOTP secret
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    otpauth_url = totp.provisioning_uri(name=user.email, issuer_name=MFA_ISSUER)

    # Generate backup codes (bcrypt hashed)
    backup_codes, backup_hashes = _generate_backup_codes()

    # Store in database
    user.mfa_secret = secret
    user.mfa_backup_codes = backup_hashes
    user.mfa_enabled = True
    await db.flush()

    logger.info("MFA enabled for user %s (%d backup codes generated)", user.email, len(backup_codes))

    return MFASetupResponse(
        secret=secret,
        otpauth_url=otpauth_url,
        qr_code_url="/api/v1/auth/mfa/qr",
        backup_codes=backup_codes,
    )


@router.get("/mfa/qr")
async def mfa_qr_code(
    user: Annotated[User, Depends(_get_current_user)],
):
    """Generate a QR code SVG for the user's MFA setup.

    Scan with Google Authenticator, Authy, or any TOTP app.
    """
    if not user.mfa_enabled or not user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA not set up. Call /mfa/setup first.")

    try:
        import pyotp
    except ImportError:
        raise HTTPException(status_code=501, detail="pyotp not installed")

    totp = pyotp.TOTP(user.mfa_secret)
    otpauth_url = totp.provisioning_uri(name=user.email, issuer_name=MFA_ISSUER)

    svg_content = _generate_qr_code_svg(otpauth_url)

    return StreamingResponse(
        io.BytesIO(svg_content.encode("utf-8")),
        media_type="image/svg+xml",
        headers={"Content-Disposition": "inline; filename=mfa-qr.svg"},
    )


@router.post("/mfa/verify")
async def mfa_verify(
    req: MFAVerifyRequest,
    user: Annotated[User, Depends(_get_current_user)],
):
    """Verify a TOTP code (for testing MFA setup before requiring it)."""
    if not user.mfa_enabled or not user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA not set up")

    try:
        import pyotp
    except ImportError:
        raise HTTPException(status_code=501, detail="pyotp not installed")

    totp = pyotp.TOTP(user.mfa_secret)
    if totp.verify(req.totp_code, valid_window=TOTP_VALID_WINDOW):
        return {"verified": True, "message": "TOTP code is valid"}
    else:
        raise HTTPException(status_code=400, detail="Invalid TOTP code")


@router.post("/mfa/disable")
async def mfa_disable(
    req: MFADisableRequest,
    user: Annotated[User, Depends(_get_current_user)],
    db: AsyncSession = Depends(get_db_session),
):
    """Disable MFA for the authenticated user.

    Requires the current TOTP code to prevent unauthorized MFA removal.
    This is a security-critical operation — audit logged.
    """
    if not user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is not enabled")

    try:
        import pyotp
    except ImportError:
        raise HTTPException(status_code=501, detail="pyotp not installed")

    # Verify current TOTP before disabling
    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(req.totp_code, valid_window=TOTP_VALID_WINDOW):
        logger.warning("MFA disable failed — invalid TOTP for user %s", user.email)
        raise HTTPException(status_code=401, detail="Invalid TOTP code. MFA cannot be disabled.")

    # Disable MFA
    user.mfa_enabled = False
    user.mfa_secret = None
    user.mfa_backup_codes = None
    await db.flush()

    logger.warning("MFA DISABLED for user %s (self-service, TOTP verified)", user.email)

    return {
        "mfa_enabled": False,
        "message": "MFA has been disabled. You should re-enable it for account security.",
    }


@router.get("/me")
async def get_current_user_info(user: Annotated[User, Depends(_get_current_user)]):
    """Get current user profile."""
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "preferred_language": user.preferred_language,
        "mfa_enabled": user.mfa_enabled,
        "backup_codes_remaining": len(user.mfa_backup_codes) if user.mfa_backup_codes else 0,
        "created_at": user.created_at.isoformat(),
    }
