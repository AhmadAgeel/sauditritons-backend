"""Restore a real encrypted dump into a disposable local PostgreSQL database."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REQUIRED_TOOLS = ("initdb", "pg_ctl", "createdb", "psql", "pg_dump", "pg_restore", "age", "age-keygen")
BACKUP_MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "routers" / "backup.py"
SPEC = importlib.util.spec_from_file_location("backup_restore_under_test", BACKUP_MODULE_PATH)
assert SPEC and SPEC.loader
backup_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backup_module)


@unittest.skipUnless(all(shutil.which(tool) for tool in REQUIRED_TOOLS), "Postgres and age tools required")
class BackupRestoreIntegrationTests(unittest.TestCase):
    def test_encrypted_backup_restores_rows(self) -> None:
        # macOS has a short Unix-socket path limit; use /private/tmp directly.
        with tempfile.TemporaryDirectory(prefix="ssa-", dir="/private/tmp") as root_string:
            root = Path(root_string)
            data = root / "data"
            socket = root / "socket"
            socket.mkdir()
            port = 54329
            subprocess.run(
                ["initdb", "-D", str(data), "-A", "trust", "-U", "postgres", "--no-instructions"],
                check=True, capture_output=True,
            )
            subprocess.run(
                ["pg_ctl", "-D", str(data), "-l", str(root / "postgres.log"), "-o",
                 f"-k {socket} -p {port} -c listen_addresses='' -c unix_socket_permissions=0700",
                 "-w", "start"],
                check=True, capture_output=True, timeout=25,
            )
            try:
                connection = ["-h", str(socket), "-p", str(port), "-U", "postgres"]
                subprocess.run(["createdb", *connection, "source"], check=True, capture_output=True)
                subprocess.run(
                    ["psql", *connection, "source", "-v", "ON_ERROR_STOP=1", "-c",
                     "CREATE TABLE backup_probe (id integer PRIMARY KEY, label text); "
                     "INSERT INTO backup_probe VALUES (1, 'first'), (2, 'second');"],
                    check=True, capture_output=True,
                )
                identity = root / "identity.txt"
                subprocess.run(["age-keygen", "-o", str(identity)], check=True, capture_output=True)
                recipient = subprocess.check_output(
                    ["age-keygen", "-y", str(identity)], text=True
                ).strip()
                backup_dir = root / "backup"
                backup_dir.mkdir()
                with patch.object(backup_module.settings, "database_hostname", str(socket)), \
                     patch.object(backup_module.settings, "database_port", port), \
                     patch.object(backup_module.settings, "database_username", "postgres"), \
                     patch.object(backup_module.settings, "database_name", "source"), \
                     patch.object(backup_module.settings, "database_password", ""), \
                     patch.object(backup_module.settings, "backup_age_recipient", recipient):
                    encrypted = backup_module.create_encrypted_dump(backup_dir)
                restored_dump = root / "restored.dump"
                subprocess.run(
                    ["age", "--decrypt", "--identity", str(identity), "--output",
                     str(restored_dump), str(encrypted)],
                    check=True, capture_output=True,
                )
                subprocess.run(["createdb", *connection, "restored"], check=True, capture_output=True)
                subprocess.run(
                    ["pg_restore", *connection, "--no-owner", "--no-acl",
                     "--dbname", "restored", str(restored_dump)],
                    check=True, capture_output=True,
                )
                count = subprocess.check_output(
                    ["psql", *connection, "restored", "-tAc", "SELECT count(*) FROM backup_probe"],
                    text=True,
                ).strip()
                self.assertEqual(count, "2")
            finally:
                subprocess.run(["pg_ctl", "-D", str(data), "-m", "immediate", "-w", "stop"],
                               check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
