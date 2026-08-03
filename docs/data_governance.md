# Data Governance — Sovereign Resource DAO

## 1. Data Ownership

| Data Category         | Owner                  | Contact                    |
|-----------------------|------------------------|----------------------------|
| User accounts         | Platform Team          | platform@mining-sa.com     |
| Geological data       | Geological Survey Dept | geology@mining-sa.com      |
| Mineral occurrences   | Exploration Team       | exploration@mining-sa.com  |
| Observations / photos | Field Operations       | field@mining-sa.com        |
| Geochemical samples   | Geochemistry Lab       | geochem@mining-sa.com      |
| Mining site records   | Compliance / Licensing | compliance@mining-sa.com   |
| Document embeddings   | Data Engineering       | data-eng@mining-sa.com     |
| Audit logs            | Security Team          | security@mining-sa.com     |

## 2. Data Classification

| Level        | Description                                   | Examples                                    |
|--------------|-----------------------------------------------|---------------------------------------------|
| **Public**   | Open geological datasets, published surveys   | Geological unit names, rock type taxonomy   |
| **Internal** | Operational data not intended for public use  | Mineral occurrence grades, site coordinates |
| **Confidential** | Sensitive business data                  | License details, XRF analysis, AI models    |
| **Restricted**   | Personal data / credentials                | User PII, MFA secrets, hashed passwords     |

## 3. Licensing & Attribution

- **Geological data** sourced from national geological surveys must retain original attribution.
- **Satellite imagery** subject to provider license terms (e.g., Sentinel: CC-BY).
- **XRF / geochemical data** generated on-site is proprietary to the operating entity.
- **AI analysis results** are derivative works; licensing follows source data terms.

All data exports include a `source` field and `license` metadata in the `properties` JSONB column.

## 4. GDPR / Data Protection Compliance

### 4.1 Personal Data Inventory

| Field              | Table     | Purpose            | Legal Basis         | Retention  |
|--------------------|-----------|--------------------|---------------------|------------|
| `email`            | users     | Account identity   | Contract            | Account lifetime + 30 days |
| `username`         | users     | Display name       | Contract            | Account lifetime + 30 days |
| `hashed_password`  | users     | Authentication     | Contract            | Account lifetime |
| `full_name`        | users     | Personalization    | Consent             | Until withdrawn |
| `phone`            | users     | 2FA / recovery     | Consent             | Until withdrawn |
| `mfa_secret`       | users     | TOTP generation    | Contract            | Account lifetime |
| `last_login_ip`    | users     | Security auditing  | Legitimate interest | 90 days (auto-purge) |
| `ip_address`       | audit_logs| Audit trail        | Legitimate interest | 90 days (auto-purge) |
| `user_agent`       | audit_logs| Security forensics | Legitimate interest | 90 days (auto-purge) |

### 4.2 Data Subject Rights

| Right               | Implementation                                          |
|---------------------|---------------------------------------------------------|
| **Access** (Art. 15) | API endpoint `GET /api/v1/users/me/export` returns all user data as JSON |
| **Rectification** (Art. 16) | Users can update profile via `PATCH /api/v1/users/me` |
| **Erasure** (Art. 17) | `DELETE /api/v1/users/me` triggers anonymization + cascade delete |
| **Portability** (Art. 20) | Export includes observations, photos, analysis in machine-readable JSON |
| **Objection** (Art. 21) | Users can opt out of AI analysis via profile settings |

### 4.3 Data Minimization

- Only collect fields required for the stated purpose.
- `full_name` and `phone` are optional; app functions without them.
- Observations store `client_id` (UUID) for offline sync, not device identifiers.
- Geo-location is stored as POINT geometry (not raw GPS traces).

### 4.4 Right to Erasure — Cascade Policy

When a user account is deleted:
1. User PII is anonymized (email → `deleted_<hash>@anonymized`, username → `deleted_<hash>`)
2. Observations are reassigned to a system "orphan" user (preserves geological data integrity)
3. Audit logs referencing the user retain `user_id` but all personal fields are cleared
4. MFA secrets are securely wiped (encrypted column key rotation)

### 4.5 Data Breach Response

1. **Detection**: Audit log anomalies trigger alerts (failed logins, bulk data access)
2. **Containment**: Revoke sessions, rotate encryption keys
3. **Notification**: DPA within 72 hours (Art. 33), affected users without undue delay (Art. 34)
4. **Documentation**: Incident logged in `audit_logs` with action `security_breach`

## 5. Audit Log Retention

- **Default retention**: 90 days
- **Purge mechanism**: PostgreSQL function `purge_old_audit_logs(90)` scheduled daily via pg_cron at 03:00 UTC
- **Manual purge**: `SELECT purge_old_audit_logs(retention_days);`
- **Compliance override**: For legal holds, set retention to 365 days or longer per jurisdiction

```sql
-- Check retention status
SELECT MIN(created_at) AS oldest_log, COUNT(*) AS total_logs FROM audit_logs;

-- Manual purge (custom retention)
SELECT purge_old_audit_logs(30);  -- keep only 30 days
```

## 6. Encryption at Rest

- `mfa_secret` column: AES-256-GCM via `EncryptedString` SQLAlchemy type
- Database-level: Enable PostgreSQL `pgcrypto` or transparent disk encryption (LUKS / cloud KMS)
- Backups: Encrypted with GPG before upload to object storage

## 7. Access Control

- All API endpoints require JWT authentication
- Admin-only endpoints require `is_admin = true` claim
- Database connections use TLS (`sslmode=verify-full`)
- Row-level security (RLS) can be enabled per-table for multi-tenant scenarios

## 8. Cross-Border Data Transfer

- Primary data center: [specify region]
- No personal data transferred outside EEA without adequacy decision or SCCs
- Geological data (non-personal) can be shared internationally per survey license terms

---

*Last updated: 2026-07-25*
*Review schedule: Quarterly or upon regulatory change*
