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

Set local database credentials, a strong `SECRET_KEY`, and the frontend origin in `.env`. To bootstrap the first administrator, set `BOOTSTRAP_ADMIN_EMAIL` to the email address that will create the first admin account. Keep `WHATSAPP_ENABLED=false` until WhatsApp credentials are configured.

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
