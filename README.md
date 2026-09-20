# SaudiTritons API

FastAPI backend for the Saudi Students Association website. It stores events, account-free RSVPs, tickets, member profiles, announcements, resources, board members, roles, check-ins, and administrative audit history in PostgreSQL.

## Local setup

Requirements:

- Python 3.12
- PostgreSQL
- Redis

Create a virtual environment, install dependencies, and configure the service:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Set local database credentials, a strong `SECRET_KEY`, and the frontend origin in `.env`. To bootstrap the first administrator, set `BOOTSTRAP_ADMIN_EMAIL` to an existing account email. On startup, that account is promoted only when the database has no administrator. Keep `WHATSAPP_ENABLED=false` until WhatsApp credentials are configured.

Transactional email defaults to ZeptoMail for backwards compatibility. The recommended low-cost production option is Resend: verify `sauditritons.org`, then set `EMAIL_PROVIDER=resend`, `RESEND_API_KEY`, `AUTH_EMAIL_FROM` (for example `SSA <signin@sauditritons.org>`), and `AUTH_EMAIL_REPLY_TO`. Publish Resend's DKIM/SPF records before switching production. Postmark remains supported with `EMAIL_PROVIDER=postmark` and `POSTMARK_SERVER_TOKEN`.

Guest RSVP can be protected with Cloudflare Turnstile without moving DNS to Cloudflare. Create a widget for `sauditritons.org` and `www.sauditritons.org`; add its public key to the frontend as `VITE_TURNSTILE_SITE_KEY`, then set the matching secret here as `TURNSTILE_SECRET_KEY`. Server validation is enforced only when the secret is present, so add the frontend key first during rollout. `TURNSTILE_ALLOWED_HOSTNAMES` is a comma-separated allowlist.

Apple Wallet passes require an Apple Developer Pass Type ID certificate. Set `APPLE_WALLET_PASS_TYPE_IDENTIFIER`, `APPLE_WALLET_TEAM_IDENTIFIER`, and base64-encoded signing certificate, private key, and Apple WWDR certificate values. The ticket endpoint returns a signed `.pkpass` only when all five values are present; QR tickets and door scanning continue to work without Wallet credentials.

Apply migrations and run the API:

```sh
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open the API reference at `http://127.0.0.1:8000/docs`.

## Roles

- `member`: public account and profile features
- `content_editor`: events, announcements, resources, and board content
- `officer`: content permissions plus RSVP operations and check-in
- `admin`: member moderation, role management, and audit history

The API prevents demoting the final administrator.

## Main endpoints

- `/events`: published events and account-free RSVP
- `/ticket`: public ticket lookup and ticket event stream
- `/content`: published announcements, resources, and board
- `/student-profiles`: member directory and profile management
- `/admin`: role-protected content, members, RSVPs, check-in, and audit operations

The older `/internal` routes remain authenticated for compatibility, but the current website uses `/admin` for daily operations.

## Production dependencies

Production requires hosted PostgreSQL and Redis, HTTPS frontend and API URLs, secure cookies, permitted CORS origins, and provider credentials for email. Images and PDFs should use an object-storage provider and store only their URLs in PostgreSQL.

Event image uploads support Cloudflare R2, AWS S3, Railway Buckets, and other S3-compatible providers through the `OBJECT_STORAGE_*` variables in `.env.example`. The admin upload route stores a high-quality WebP object and returns its HTTPS URL. Railway Buckets stay private and are served through the validated `/media/events/...` API route. Operational health checks, scheduled smoke tests, and backup instructions are documented in `OPERATIONS.md`.
