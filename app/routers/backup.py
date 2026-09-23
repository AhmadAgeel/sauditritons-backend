"""A narrowly authenticated, encrypted database export for scheduled backups."""

from __future__ import annotations

import hmac
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.config import settings
from app.redis import redis_client


router = APIRouter()
MAX_BACKUP_BYTES = 25 * 1024 * 1024
BACKUP_COOLDOWN_SECONDS = 300


def authorize_export(authorization: str | None) -> None:
    token = settings.backup_export_token
    if not token or len(token) < 32 or not settings.backup_age_recipient:
        raise HTTPException(status_code=503, detail="Database backup is not configured")
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not authorization or supplied == authorization or not hmac.compare_digest(supplied, token):
        raise HTTPException(status_code=401, detail="Unauthorized")


def create_encrypted_dump(directory: Path) -> Path:
    dump = directory / "database.dump"
    encrypted = directory / "database.dump.age"
    environment = os.environ.copy()
    environment["PGPASSWORD"] = settings.database_password

    # Keep the password out of process arguments and leave the database on
    # Railway's private network. Never return or log the plaintext dump.
    with dump.open("wb") as output:
        os.chmod(dump, 0o600)
        result = subprocess.run(
            [
                "pg_dump",
                "--host", settings.database_hostname,
                "--port", str(settings.database_port),
                "--username", settings.database_username,
                "--dbname", settings.database_name,
                "--format=custom", "--no-owner", "--no-acl",
            ],
            stdout=output,
            stderr=subprocess.DEVNULL,
            env=environment,
            timeout=120,
            check=False,
        )
    if result.returncode != 0 or dump.stat().st_size < 5:
        raise RuntimeError("pg_dump failed")
    with dump.open("rb") as input_file:
        if input_file.read(5) != b"PGDMP":
            raise RuntimeError("pg_dump returned an invalid archive")
    if dump.stat().st_size > MAX_BACKUP_BYTES:
        raise RuntimeError("Database backup exceeds the size limit")

    subprocess.run(
        ["pg_restore", "--list", str(dump)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
        check=True,
    )
    subprocess.run(
        ["age", "--encrypt", "--recipient", settings.backup_age_recipient,
         "--output", str(encrypted), str(dump)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
        check=True,
    )
    if encrypted.stat().st_size > MAX_BACKUP_BYTES:
        raise RuntimeError("Encrypted database backup exceeds the size limit")
    with encrypted.open("rb") as input_file:
        if input_file.read(21) != b"age-encryption.org/v1":
            raise RuntimeError("Database backup encryption failed")
    dump.unlink()
    return encrypted


@router.post("/internal/backups/database", include_in_schema=False)
def export_database_backup(authorization: str | None = Header(default=None)):
    authorize_export(authorization)
    try:
        allowed = redis_client.set("database_backup_export_cooldown", "1", nx=True, ex=BACKUP_COOLDOWN_SECONDS)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Backup unavailable") from exc
    if not allowed:
        raise HTTPException(status_code=429, detail="Backup recently requested")

    temporary = tempfile.TemporaryDirectory(prefix="ssa-backup-")
    try:
        encrypted = create_encrypted_dump(Path(temporary.name))
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return FileResponse(
            encrypted,
            media_type="application/octet-stream",
            filename=f"sauditritons-{stamp}.dump.age",
            background=BackgroundTask(temporary.cleanup),
            headers={"Cache-Control": "no-store"},
        )
    except Exception as exc:
        temporary.cleanup()
        try:
            redis_client.delete("database_backup_export_cooldown")
        except Exception:
            pass
        raise HTTPException(status_code=503, detail="Backup failed") from exc
