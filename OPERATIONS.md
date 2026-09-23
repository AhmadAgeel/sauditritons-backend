# Production Operations

## Health and monitoring

- `GET /health` confirms the API process is running.
- `GET /health/ready` checks PostgreSQL and Redis and returns `503` if either dependency is unavailable.
- `.github/workflows/production-smoke.yml` checks the website, readiness endpoint, and public events twice per hour. Keep GitHub Actions failure notifications enabled for repository administrators.

## Database backups

The daily **Production database backup** GitHub Action calls a token-protected export on the existing API. The API runs `pg_dump` inside Railway's private network, validates and encrypts the archive with `age`, and returns only ciphertext. GitHub retains that ciphertext as an artifact for seven days. No public database proxy, Railway SSH connection, new bucket, or paid backup plan is required. This is **not active** until the credentials below are configured and a manual run succeeds.

Scheduled runs are disabled unless the repository variable `BACKUP_ENABLED` is `true`; manual runs remain available for testing. Ahmed's deployment repository intentionally keeps the variable unset. Configure the workflow in `falsenayin/sauditritons-backend` under **Settings → Secrets and variables → Actions**:

- GitHub Actions repository secret `BACKUP_EXPORT_TOKEN`: a random 32+ character token.
- GitHub Actions repository variable `BACKUP_ENABLED=true`: set only after the backend is deployed, the secret is present, and a manual backup and restore have passed.
- Railway backend service variable `BACKUP_EXPORT_TOKEN`: the same token. It authorizes only encrypted backup exports; never put it in source control or the frontend.
- Railway backend service variable `BACKUP_AGE_RECIPIENT`: the public recipient from `age-keygen -y /path/to/backup-identity.txt`. Store the corresponding **private identity offline**, in at least two secure locations; do not upload it to GitHub, Railway, or the database server.

GitHub Actions cannot read Railway service variables automatically. The workflow names missing configuration without printing values. Before merging this scheduled workflow to `main`, confirm the repository's Actions/artifact storage budget is capped at $0 and unused storage is available. Each backup is capped at 25 MiB, and seven daily artifacts can use up to 175 MiB of GitHub's shared storage allowance. An oversized database causes the run to fail rather than incur unbounded storage use. GitHub artifacts are accessible to people with repository read access, so **never** remove the API-side encryption step.

Trigger **Production database backup → Run workflow** manually. Confirm it succeeds, download its `ssa-postgres-...` artifact, and test decryption and restoration into a disposable database before relying on the schedule. To decrypt:

```sh
age --decrypt --identity /path/to/backup-identity.txt --output database.dump sauditritons-*.dump.age
pg_restore --list database.dump >/dev/null
```

Then restore to an **empty, non-production** PostgreSQL database:

```sh
pg_restore --clean --if-exists --no-owner --no-acl --dbname "$RESTORE_DATABASE_URL" database.dump
```

Never test restoration against production. Perform a quarterly restore into a temporary database and verify event, member, RSVP, and check-in counts. If the seven-day retention, size cap, or GitHub storage budget becomes insufficient, stop and choose a longer-term storage plan; GitHub artifacts are not archival storage.

## Event image storage

The API accepts S3-compatible storage, including Cloudflare R2, AWS S3, and Railway Buckets. Configure the `OBJECT_STORAGE_*` variables documented in `.env.example`. New event uploads are normalized to high-quality WebP and stored under `events/`; PostgreSQL stores only the public API URL.

For a Railway Bucket, use the credentials shown in the bucket's **Credentials** tab and set:

- `OBJECT_STORAGE_URL_STYLE=virtual`
- `OBJECT_STORAGE_PUBLIC_BASE_URL=https://api.sauditritons.org/media`

Railway Buckets are private. The API's `/media/events/<id>.webp` route reads only validated event-image keys and adds immutable browser caching; do not expose the bucket credentials or attempt to make the bucket public.

## Incident response

1. Put the frontend into maintenance mode only if data integrity is at risk.
2. Preserve Railway logs and note the first failing request ID.
3. Revoke exposed credentials before redeploying.
4. Restore data into a temporary database and compare it before changing production.
5. Record the incident and corrective action in the repository.
