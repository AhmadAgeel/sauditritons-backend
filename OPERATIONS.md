# Production Operations

## Health and monitoring

- `GET /health` confirms the API process is running.
- `GET /health/ready` checks PostgreSQL and Redis and returns `503` if either dependency is unavailable.
- `.github/workflows/production-smoke.yml` checks the website, readiness endpoint, and public events twice per hour. Keep GitHub Actions failure notifications enabled for repository administrators.

## Database backups

Prefer enabling Railway PostgreSQL volume backups in the Postgres service's **Backups** tab. Keep at least seven daily restore points.

The repository also includes an independent daily backup workflow. It runs on GitHub-hosted runners, outside Railway's private network. In **Settings → Secrets and variables → Actions** for `AhmadAgeel/sauditritons-backend`, add these repository secrets:

- `PRODUCTION_DATABASE_URL`: the Postgres service's **public TCP proxy** connection URL, not a `railway.internal` address. Enable TCP Proxy in the Postgres service if no public URL exists. Use a read-only database account if one is available.
- `BACKUP_S3_ENDPOINT_URL`: the storage bucket's S3 endpoint (optional only for AWS S3).
- `BACKUP_S3_REGION`: the bucket region, or `auto` for Railway Buckets.
- `BACKUP_S3_URL_STYLE`: `virtual` for Railway Buckets; `path` for older S3-compatible buckets.
- `BACKUP_S3_ACCESS_KEY_ID`, `BACKUP_S3_SECRET_ACCESS_KEY`, `BACKUP_S3_BUCKET`: the credentials and exact bucket name from the bucket's **Credentials** tab. Prefer a dedicated private backup bucket with restricted access.

Railway service variables do not automatically become GitHub Actions secrets. The workflow fails at **Verify backup secrets** if any required GitHub secret is missing, and names the missing entries without printing their values.

Run **Production database backup** manually once and verify the resulting `database/YYYY/MM/*.dump.gz` object before relying on its schedule.

To restore, download and decompress a backup, provision an empty PostgreSQL database, then run:

```sh
pg_restore --clean --if-exists --no-owner --no-acl --dbname "$RESTORE_DATABASE_URL" database.dump
```

Never test restoration against production. Perform a quarterly restore into a temporary database and verify event, member, RSVP, and check-in counts.

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
