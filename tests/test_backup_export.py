"""The API must never return a plaintext database dump."""

from __future__ import annotations

import os
import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

BACKUP_MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "routers" / "backup.py"
SPEC = importlib.util.spec_from_file_location("backup_export_under_test", BACKUP_MODULE_PATH)
assert SPEC and SPEC.loader
backup_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backup_module)
authorize_export = backup_module.authorize_export
create_encrypted_dump = backup_module.create_encrypted_dump


@unittest.skipUnless(shutil.which("age") and shutil.which("age-keygen"), "age is required")
class BackupExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.identity = self.root / "identity.txt"
        subprocess.run(["age-keygen", "-o", str(self.identity)], check=True, capture_output=True)
        self.recipient = subprocess.check_output(
            ["age-keygen", "-y", str(self.identity)], text=True
        ).strip()
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        self.pg_dump = bin_dir / "pg_dump"
        self.pg_restore = bin_dir / "pg_restore"
        self.pg_dump.write_text("#!/bin/sh\nprintf 'PGDMPtest-archive-content'\n")
        self.pg_restore.write_text("#!/bin/sh\nexit 0\n")
        self.pg_dump.chmod(0o755)
        self.pg_restore.chmod(0o755)
        self.path = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"

    def test_requires_the_exact_bearer_token(self) -> None:
        with patch.object(backup_module.settings, "backup_export_token", "a" * 48), patch.object(
            backup_module.settings, "backup_age_recipient", self.recipient
        ):
            authorize_export("Bearer " + "a" * 48)
            for value in (None, "a" * 48, "Bearer wrong"):
                with self.subTest(value=value), self.assertRaises(HTTPException) as context:
                    authorize_export(value)
                self.assertEqual(context.exception.status_code, 401)

    def test_disabled_until_both_settings_are_present(self) -> None:
        with patch.object(backup_module.settings, "backup_export_token", ""):
            with self.assertRaises(HTTPException) as context:
                authorize_export("Bearer anything")
            self.assertEqual(context.exception.status_code, 503)

    def test_encrypted_export_decrypts_to_validated_dump(self) -> None:
        with patch.dict(os.environ, {"PATH": self.path}), patch.object(
            backup_module.settings, "backup_age_recipient", self.recipient
        ):
            encrypted = create_encrypted_dump(self.root)
        self.assertTrue(encrypted.read_bytes().startswith(b"age-encryption.org/v1"))
        self.assertFalse((self.root / "database.dump").exists())
        plaintext = subprocess.check_output(
            ["age", "--decrypt", "--identity", str(self.identity), str(encrypted)]
        )
        self.assertEqual(plaintext, b"PGDMPtest-archive-content")

    def test_rejects_invalid_dump_before_encryption(self) -> None:
        self.pg_dump.write_text("#!/bin/sh\nprintf 'not a dump'\n")
        with patch.dict(os.environ, {"PATH": self.path}), patch.object(
            backup_module.settings, "backup_age_recipient", self.recipient
        ), self.assertRaises(RuntimeError):
            create_encrypted_dump(self.root)
        self.assertFalse((self.root / "database.dump.age").exists())

    def test_http_route_returns_only_ciphertext(self) -> None:
        app = FastAPI()
        app.include_router(backup_module.router)
        with patch.dict(os.environ, {"PATH": self.path}), \
             patch.object(backup_module.settings, "backup_export_token", "a" * 48), \
             patch.object(backup_module.settings, "backup_age_recipient", self.recipient), \
             patch.object(backup_module.redis_client, "set", return_value=True):
            with TestClient(app) as client:
                unauthorized = client.post("/internal/backups/database")
                self.assertEqual(unauthorized.status_code, 401)
                response = client.post(
                    "/internal/backups/database",
                    headers={"Authorization": "Bearer " + "a" * 48},
                )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.content.startswith(b"age-encryption.org/v1"))
        self.assertNotIn(b"PGDMP", response.content)
        self.assertEqual(response.headers["cache-control"], "no-store")


if __name__ == "__main__":
    unittest.main()
