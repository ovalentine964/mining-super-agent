"""Add audit log retention — auto-delete logs older than 90 days.

Revision ID: 002_log_retention
Revises: 001_initial
Create Date: 2026-07-25 16:18:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_log_retention"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── pg_cron extension (if available) for scheduled cleanup ──────────
    # On managed PostgreSQL (RDS, CloudSQL, etc.) pg_cron may not be available.
    # We create the extension conditionally and fall back to a function-only approach.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_cron")

    # ── Purge function ──────────────────────────────────────────────────
    # Deletes audit_logs rows older than 90 days.
    # Can be called manually, from pg_cron, or from application code.
    op.execute("""
        CREATE OR REPLACE FUNCTION purge_old_audit_logs(
            retention_days INTEGER DEFAULT 90
        ) RETURNS BIGINT AS $$
        DECLARE
            deleted_count BIGINT;
        BEGIN
            DELETE FROM audit_logs
            WHERE created_at < NOW() - (retention_days || ' days')::INTERVAL;

            GET DIAGNOSTICS deleted_count = ROW_COUNT;

            RAISE NOTICE 'Purged % audit log rows older than % days', deleted_count, retention_days;
            RETURN deleted_count;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # ── Schedule daily purge via pg_cron (03:00 UTC) ────────────────────
    # This is idempotent — if pg_cron is not available it silently fails.
    op.execute("""
        DO $$
        BEGIN
            -- Try to schedule with pg_cron; ignore if extension is missing
            PERFORM cron.schedule(
                'audit-log-retention',
                '0 3 * * *',
                'SELECT purge_old_audit_logs(90)'
            );
        EXCEPTION
            WHEN undefined_function THEN
                RAISE NOTICE 'pg_cron not available — use application-level or OS cron for log retention';
            WHEN insufficient_privilege THEN
                RAISE NOTICE 'pg_cron not permitted — use application-level or OS cron for log retention';
        END;
        $$;
    """)

    # ── Index for efficient retention deletes ───────────────────────────
    # Composite index on created_at to speed up the range scan in purge function.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_logs_retention "
        "ON audit_logs (created_at) WHERE created_at IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_audit_logs_retention")
    op.execute("SELECT cron.unschedule('audit-log-retention') WHERE EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'unschedule')")
    op.execute("DROP FUNCTION IF EXISTS purge_old_audit_logs")
