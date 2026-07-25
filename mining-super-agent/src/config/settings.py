"""
Mining Super-Agent — Pydantic Settings
Refuses to start if critical secrets are not set.
"""

from __future__ import annotations

import sys
from enum import Enum
from functools import lru_cache
from typing import Annotated

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Critical secrets (JWT keys, DB password, encryption key) cause
    an immediate sys.exit(1) if missing — the app must NEVER start
    with insecure defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────────
    app_env: AppEnvironment = Field(default=AppEnvironment.PRODUCTION)
    log_level: str = Field(default="INFO")
    debug: bool = Field(default=False)

    # ── Domain & CORS ───────────────────────────────────────────
    domain: str = Field(default="localhost")
    cors_origins: str = Field(
        default="",
        description="Comma-separated allowed origins. NO wildcards.",
    )

    # ── JWT Authentication ──────────────────────────────────────
    jwt_secret_key: SecretStr = Field(default=SecretStr(""))
    jwt_refresh_secret_key: SecretStr = Field(default=SecretStr(""))
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=15)
    jwt_refresh_token_expire_days: int = Field(default=7)

    # ── API Key Encryption ──────────────────────────────────────
    api_keys_encryption_key: SecretStr = Field(default=SecretStr(""))

    # ── Database Column Encryption ────────────────────────────────
    encryption_key: SecretStr = Field(
        default=SecretStr(""),
        description="Fernet key for database column encryption. Comma-separated for key rotation.",
    )

    # ── MFA ─────────────────────────────────────────────────────
    mfa_issuer_name: str = Field(
        default="Mining Super-Agent",
        description="Issuer name shown in authenticator apps.",
    )

    # ── PostgreSQL ──────────────────────────────────────────────
    postgres_db: str = Field(default="mining")
    postgres_user: str = Field(default="mining")
    db_password: SecretStr = Field(default=SecretStr(""))
    database_url: str = Field(
        default="",
        description="Full async URL. Constructed from components if empty.",
    )
    database_url_sync: str = Field(
        default="",
        description="Full sync URL for migrations. Constructed if empty.",
    )

    # ── Redis ───────────────────────────────────────────────────
    redis_url: str = Field(
        default="",
        description="Full Redis URL with password. Constructed if empty.",
    )
    redis_password: SecretStr = Field(default=SecretStr(""))

    # ── Qdrant ──────────────────────────────────────────────────
    qdrant_url: str = Field(default="http://localhost:6333")
    qdrant_collection: str = Field(default="mining_embeddings")

    # ── MinIO ───────────────────────────────────────────────────
    minio_endpoint: str = Field(default="localhost:9000")
    minio_access_key: str = Field(default="")
    minio_secret_key: SecretStr = Field(default=SecretStr(""))
    minio_secure: bool = Field(default=False)
    minio_bucket: str = Field(default="mining-data")

    # ── External AI APIs ────────────────────────────────────────
    nvidia_api_key: SecretStr = Field(default=SecretStr(""))
    groq_api_key: SecretStr = Field(default=SecretStr(""))
    google_ai_api_key: SecretStr = Field(default=SecretStr(""))
    together_api_key: SecretStr = Field(default=SecretStr(""))
    mistral_api_key: SecretStr = Field(default=SecretStr(""))

    # ── Telegram ────────────────────────────────────────────────
    telegram_bot_token: SecretStr = Field(default=SecretStr(""))

    # ── Satellite ───────────────────────────────────────────────
    copernicus_client_id: str = Field(default="")
    copernicus_client_secret: SecretStr = Field(default=SecretStr(""))

    # ── Market Data ─────────────────────────────────────────────
    finnhub_api_key: SecretStr = Field(default=SecretStr(""))
    alpha_vantage_api_key: SecretStr = Field(default=SecretStr(""))

    # ── Backup ──────────────────────────────────────────────────
    backup_s3_bucket: str = Field(default="")
    backup_s3_region: str = Field(default="")
    backup_s3_access_key: str = Field(default="")
    backup_s3_secret_key: SecretStr = Field(default=SecretStr(""))
    backup_s3_endpoint: str = Field(default="")
    backup_kms_key_id: str = Field(default="")

    # ── Computed Properties ─────────────────────────────────────

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse CORS origins string into list. Rejects wildcards."""
        if not self.cors_origins:
            return []
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        for origin in origins:
            if origin == "*" or ".*" in origin:
                raise ValueError(
                    f"WILDCARD CORS ORIGIN REJECTED: '{origin}'. "
                    "Set explicit origins in CORS_ORIGINS."
                )
        return origins

    @property
    def async_database_url(self) -> str:
        """Get async database URL (postgresql+asyncpg)."""
        if self.database_url:
            return self.database_url
        pw = self.db_password.get_secret_value()
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{pw}"
            f"@postgres:5432/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """Get sync database URL (postgresql) for migrations."""
        if self.database_url_sync:
            return self.database_url_sync
        pw = self.db_password.get_secret_value()
        return (
            f"postgresql://{self.postgres_user}:{pw}"
            f"@postgres:5432/{self.postgres_db}"
        )

    @property
    def full_redis_url(self) -> str:
        """Get Redis URL with password."""
        if self.redis_url:
            return self.redis_url
        pw = self.redis_password.get_secret_value()
        return f"redis://:{pw}@redis:6379/0"

    @property
    def is_production(self) -> bool:
        return self.app_env == AppEnvironment.PRODUCTION

    # ── Validators ──────────────────────────────────────────────

    @model_validator(mode="after")
    def _validate_critical_secrets(self) -> "Settings":
        """Refuse to start if critical secrets are not set."""
        errors: list[str] = []

        jwt_key = self.jwt_secret_key.get_secret_value()
        if not jwt_key or jwt_key.startswith("CHANGE_ME"):
            errors.append(
                "JWT_SECRET_KEY is not set or uses placeholder. "
                "Generate: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
            )

        jwt_refresh = self.jwt_refresh_secret_key.get_secret_value()
        if not jwt_refresh or jwt_refresh.startswith("CHANGE_ME"):
            errors.append(
                "JWT_REFRESH_SECRET_KEY is not set or uses placeholder. "
                "Generate: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
            )

        if self.is_production:
            db_pw = self.db_password.get_secret_value()
            if not db_pw or db_pw.startswith("CHANGE_ME"):
                errors.append(
                    "DB_PASSWORD is not set or uses placeholder. "
                    "Generate a strong password (20+ chars)."
                )

            enc_key = self.api_keys_encryption_key.get_secret_value()
            if not enc_key or enc_key.startswith("CHANGE_ME"):
                errors.append(
                    "API_KEYS_ENCRYPTION_KEY is not set. "
                    "Generate: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )

            # ENCRYPTION_KEY is always required (not just production)
            db_enc_key = self.encryption_key.get_secret_value()
            if not db_enc_key or db_enc_key.startswith("CHANGE_ME"):
                errors.append(
                    "ENCRYPTION_KEY is not set or uses placeholder. "
                    "The app CANNOT start without database encryption. "
                    "Generate: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )

            redis_pw = self.redis_password.get_secret_value()
            if not redis_pw or redis_pw.startswith("CHANGE_ME"):
                errors.append("REDIS_PASSWORD is not set or uses placeholder.")

        # ENCRYPTION_KEY is required in ALL environments
        db_enc_key = self.encryption_key.get_secret_value()
        if not db_enc_key or db_enc_key.startswith("CHANGE_ME"):
            if "ENCRYPTION_KEY is not set" not in str(errors):
                errors.append(
                    "ENCRYPTION_KEY is not set or uses placeholder. "
                    "The app CANNOT start without database encryption. "
                    "Generate: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )

        if errors:
            print("\n🚨 CRITICAL CONFIGURATION ERRORS — REFUSING TO START:\n")
            for i, err in enumerate(errors, 1):
                print(f"  {i}. {err}")
            print("\nFix these in your .env file, then restart.\n")
            sys.exit(1)

        return self

    @field_validator("cors_origins")
    @classmethod
    def _reject_wildcard_cors(cls, v: str) -> str:
        """Reject wildcard CORS origins."""
        if v:
            for origin in v.split(","):
                origin = origin.strip()
                if origin == "*":
                    raise ValueError(
                        "CORS wildcard '*' is not allowed. "
                        "List explicit origins: https://yourdomain.com"
                    )
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton settings instance. Cached after first call."""
    return Settings()
