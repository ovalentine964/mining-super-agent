#!/usr/bin/env python3
"""
API Key Rotation Script — Secure key rotation for the Mining Super-Agent.

This script handles the complete lifecycle of key rotation:
1. Generate a new encryption key
2. Re-encrypt all sensitive database fields with the new key
3. Revoke the old key (update .env)
4. Audit-log every rotation event

Supported key types:
- ENCRYPTION_KEY (Fernet — for database column encryption)
- JWT_SECRET_KEY (for JWT access tokens)
- JWT_REFRESH_SECRET_KEY (for JWT refresh tokens)

Usage:
    # Rotate the database encryption key
    python scripts/key_rotation.py --key-type encryption

    # Rotate JWT secret key
    python scripts/key_rotation.py --key-type jwt

    # Rotate JWT refresh key
    python scripts/key_rotation.py --key-type jwt-refresh

    # Rotate ALL keys
    python scripts/key_rotation.py --key-type all

    # Dry run (show what would happen)
    python scripts/key_rotation.py --key-type encryption --dry-run

Environment:
    DATABASE_URL — PostgreSQL connection string
    ENCRYPTION_KEY — Current encryption key (for DB re-encryption)
    .env — Updated in place with new keys
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import secrets
import shutil
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("key_rotation")

# ── Audit Log ────────────────────────────────────────────────────

AUDIT_LOG_PATH = PROJECT_ROOT / "logs" / "key_rotation_audit.jsonl"


def audit_log(event: dict) -> None:
    """Append an audit event to the rotation log.

    Each event is a JSON line with:
    - timestamp: ISO 8601 UTC timestamp
    - action: what was done
    - key_type: which key was rotated
    - details: additional context
    - success: whether the operation succeeded
    """
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    event["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    event["source"] = "scripts/key_rotation.py"

    with open(AUDIT_LOG_PATH, "a") as f:
        f.write(json.dumps(event, default=str) + "\n")

    logger.info("AUDIT: %s", json.dumps(event, default=str))


# ── Key Generation ───────────────────────────────────────────────

def generate_fernet_key() -> str:
    """Generate a new Fernet encryption key."""
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode("utf-8")


def generate_jwt_secret() -> str:
    """Generate a new JWT secret key."""
    return secrets.token_urlsafe(64)


# ── .env File Manipulation ───────────────────────────────────────

def read_env_file(env_path: Path) -> dict[str, str]:
    """Parse .env file into a dict."""
    env_vars: dict[str, str] = {}
    if not env_path.exists():
        return env_vars

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env_vars[key.strip()] = value.strip()
    return env_vars


def update_env_file(env_path: Path, updates: dict[str, str]) -> None:
    """Update specific keys in .env file, preserving comments and order."""
    if not env_path.exists():
        logger.error(".env file not found at %s", env_path)
        sys.exit(1)

    # Create backup
    backup_path = env_path.with_suffix(f".env.backup.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}")
    shutil.copy2(env_path, backup_path)
    logger.info("Created backup: %s", backup_path)

    with open(env_path) as f:
        lines = f.readlines()

    updated_keys: set[str] = set()
    new_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                updated_keys.add(key)
                continue
        new_lines.append(line)

    # Append any keys that weren't already in the file
    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)

    logger.info("Updated %d key(s) in %s", len(updated_keys), env_path)


# ── Database Re-encryption ───────────────────────────────────────

def reencrypt_database_columns(old_key: str, new_key: str, dry_run: bool = False) -> dict:
    """Re-encrypt all sensitive database columns with a new key.

    This connects to the database, reads encrypted values with the old key,
    and writes them back encrypted with the new key.

    Returns a dict with counts of re-encrypted fields.
    """
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    import base64

    def make_fernet(master_key_str: str) -> Fernet:
        key_bytes = master_key_str.encode() if master_key_str.startswith("gAA") else base64.urlsafe_b64decode(master_key_str)
        hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"mining-super-agent-db-encryption")
        derived = hkdf.derive(key_bytes)
        return Fernet(base64.urlsafe_b64encode(derived))

    old_fernet = make_fernet(old_key)
    new_fernet = make_fernet(new_key)

    # Columns that use encryption (table, column, type)
    encrypted_columns = [
        ("users", "mfa_secret", "string"),
        ("users", "phone", "string"),
        # Add more as encrypted columns are added to models
    ]

    database_url = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL", "")
    if not database_url:
        logger.error("DATABASE_URL not set — cannot re-encrypt database")
        return {"error": "no_database_url"}

    # Convert async URL to sync for psycopg2
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    results = {"tables_processed": 0, "rows_updated": 0, "errors": []}

    try:
        import psycopg2
        conn = psycopg2.connect(sync_url)
        conn.autocommit = False
        cursor = conn.cursor()

        for table, column, col_type in encrypted_columns:
            logger.info("Processing %s.%s", table, column)

            cursor.execute(f"SELECT id, {column} FROM {table} WHERE {column} IS NOT NULL")
            rows = cursor.fetchall()

            updated = 0
            for row_id, encrypted_value in rows:
                if not encrypted_value or not encrypted_value.startswith("gAAAAA"):
                    continue

                try:
                    plaintext = old_fernet.decrypt(encrypted_value.encode()).decode()
                    new_encrypted = new_fernet.encrypt(plaintext.encode()).decode()

                    if dry_run:
                        logger.info("  [DRY RUN] Would re-encrypt %s.%s id=%s", table, column, row_id)
                    else:
                        cursor.execute(
                            f"UPDATE {table} SET {column} = %s WHERE id = %s",
                            (new_encrypted, row_id),
                        )
                    updated += 1
                except Exception as e:
                    results["errors"].append(f"{table}.{column} id={row_id}: {e}")
                    logger.error("  Failed to re-encrypt %s.%s id=%s: %s", table, column, row_id, e)

            results["tables_processed"] += 1
            results["rows_updated"] += updated
            logger.info("  Re-encrypted %d rows in %s.%s", updated, table, column)

        if not dry_run:
            conn.commit()
            logger.info("Database re-encryption committed")
        else:
            conn.rollback()
            logger.info("[DRY RUN] All changes rolled back")

        cursor.close()
        conn.close()

    except ImportError:
        logger.error("psycopg2 not installed. Install with: pip install psycopg2-binary")
        results["errors"].append("psycopg2 not installed")
    except Exception as e:
        logger.error("Database re-encryption failed: %s", e)
        results["errors"].append(str(e))

    return results


# ── Rotation Handlers ────────────────────────────────────────────

def rotate_encryption_key(env_path: Path, dry_run: bool = False) -> bool:
    """Rotate the ENCRYPTION_KEY used for database column encryption.

    Steps:
    1. Generate new Fernet key
    2. Re-encrypt database columns with new key
    3. Update .env with new key
    4. Audit log
    """
    logger.info("=" * 60)
    logger.info("Rotating ENCRYPTION_KEY")
    logger.info("=" * 60)

    old_key = os.getenv("ENCRYPTION_KEY", "")
    if not old_key:
        logger.error("ENCRYPTION_KEY not set — cannot rotate")
        audit_log({"action": "rotate_encryption_key", "success": False, "detail": "Key not set"})
        return False

    new_key = generate_fernet_key()
    logger.info("Generated new Fernet key: %s...%s", new_key[:8], new_key[-8:])

    # Re-encrypt database
    db_result = reencrypt_database_columns(old_key, new_key, dry_run=dry_run)

    if db_result.get("errors"):
        logger.error("Database re-encryption had errors: %s", db_result["errors"])
        if not dry_run:
            audit_log({
                "action": "rotate_encryption_key",
                "success": False,
                "detail": "Database re-encryption errors",
                "errors": db_result["errors"],
            })
            return False

    # Update .env (store old key as legacy for graceful rotation)
    if dry_run:
        logger.info("[DRY RUN] Would update ENCRYPTION_KEY in %s", env_path)
        logger.info("[DRY RUN] New key: %s...%s", new_key[:8], new_key[-8:])
    else:
        # For zero-downtime rotation: new key first, old key as fallback
        combined_key = f"{new_key},{old_key}" if old_key else new_key
        update_env_file(env_path, {"ENCRYPTION_KEY": combined_key})
        logger.info("Updated ENCRYPTION_KEY in %s", env_path)
        logger.info("Old key preserved as fallback for decryption")

    audit_log({
        "action": "rotate_encryption_key",
        "success": True,
        "dry_run": dry_run,
        "rows_re_encrypted": db_result.get("rows_updated", 0),
        "tables_processed": db_result.get("tables_processed", 0),
    })

    return True


def rotate_jwt_secret(env_path: Path, dry_run: bool = False) -> bool:
    """Rotate the JWT_SECRET_KEY used for access tokens.

    Note: This invalidates ALL existing access tokens immediately.
    Users will need to re-authenticate.
    """
    logger.info("=" * 60)
    logger.info("Rotating JWT_SECRET_KEY")
    logger.info("=" * 60)

    new_secret = generate_jwt_secret()
    logger.info("Generated new JWT secret: %s...%s", new_secret[:8], new_secret[-8:])

    if dry_run:
        logger.info("[DRY RUN] Would update JWT_SECRET_KEY in %s", env_path)
    else:
        update_env_file(env_path, {"JWT_SECRET_KEY": new_secret})
        logger.info("Updated JWT_SECRET_KEY — all existing tokens are now INVALID")

    audit_log({
        "action": "rotate_jwt_secret_key",
        "success": True,
        "dry_run": dry_run,
        "warning": "All existing access tokens invalidated",
    })

    return True


def rotate_jwt_refresh_secret(env_path: Path, dry_run: bool = False) -> bool:
    """Rotate the JWT_REFRESH_SECRET_KEY used for refresh tokens.

    Note: This invalidates ALL existing refresh tokens immediately.
    Users will need to re-authenticate.
    """
    logger.info("=" * 60)
    logger.info("Rotating JWT_REFRESH_SECRET_KEY")
    logger.info("=" * 60)

    new_secret = generate_jwt_secret()
    logger.info("Generated new JWT refresh secret: %s...%s", new_secret[:8], new_secret[-8:])

    if dry_run:
        logger.info("[DRY RUN] Would update JWT_REFRESH_SECRET_KEY in %s", env_path)
    else:
        update_env_file(env_path, {"JWT_REFRESH_SECRET_KEY": new_secret})
        logger.info("Updated JWT_REFRESH_SECRET_KEY — all existing refresh tokens are now INVALID")

    audit_log({
        "action": "rotate_jwt_refresh_secret_key",
        "success": True,
        "dry_run": dry_run,
        "warning": "All existing refresh tokens invalidated",
    })

    return True


# ── Main ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Rotate encryption and authentication keys for Mining Super-Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/key_rotation.py --key-type encryption --dry-run
  python scripts/key_rotation.py --key-type jwt
  python scripts/key_rotation.py --key-type all

Key Types:
  encryption   — Fernet key for database column encryption (safe, re-encrypts DB)
  jwt          — JWT access token secret (invalidates all sessions)
  jwt-refresh  — JWT refresh token secret (invalidates all sessions)
  all          — Rotate all keys (invalidates all sessions)
        """,
    )
    parser.add_argument(
        "--key-type",
        choices=["encryption", "jwt", "jwt-refresh", "all"],
        required=True,
        help="Which key to rotate",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=PROJECT_ROOT / ".env",
        help="Path to .env file (default: ./.env)",
    )

    args = parser.parse_args()

    if not args.env_file.exists():
        logger.error(".env file not found at %s", args.env_file)
        logger.error("Copy .env.example to .env and fill in real values first.")
        sys.exit(1)

    # Load .env into os.environ for crypto operations
    from dotenv import load_dotenv
    load_dotenv(args.env_file, override=True)

    if args.dry_run:
        logger.info("🔍 DRY RUN MODE — no changes will be made")
        logger.info("")

    results: dict[str, bool] = {}

    if args.key_type in ("encryption", "all"):
        results["encryption"] = rotate_encryption_key(args.env_file, dry_run=args.dry_run)

    if args.key_type in ("jwt", "all"):
        results["jwt"] = rotate_jwt_secret(args.env_file, dry_run=args.dry_run)

    if args.key_type in ("jwt-refresh", "all"):
        results["jwt-refresh"] = rotate_jwt_refresh_secret(args.env_file, dry_run=args.dry_run)

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("ROTATION SUMMARY")
    logger.info("=" * 60)
    for key_type, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info("  %s: %s", key_type, status)

    if all(results.values()):
        logger.info("")
        logger.info("🎉 All rotations completed successfully!")
        logger.info("")
        if not args.dry_run:
            logger.info("⚠️  IMPORTANT: Restart the application to pick up new keys:")
            logger.info("    docker compose restart app")
            logger.info("")
            logger.info("📋 Audit log: %s", AUDIT_LOG_PATH)
        sys.exit(0)
    else:
        logger.error("")
        logger.error("💥 Some rotations failed. Check logs above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
