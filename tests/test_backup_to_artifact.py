"""Only encrypted output from the backend may become a GitHub artifact."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "backup_to_artifact.sh"


class BackupArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        self.curl = bin_dir / "curl"
        self.output = self.root / "github-output.txt"
        self.environment = {
            **os.environ,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "BACKUP_EXPORT_TOKEN": "test-only",
            "BACKUP_API_URL": "https://example.invalid/internal/backups/database",
            "RUNNER_TEMP": str(self.root),
            "GITHUB_OUTPUT": str(self.output),
            "MAX_BACKUP_BYTES": "1024",
        }

    def run_backup(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPT)],
            env=self.environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def write_fake_curl(self, content: str) -> None:
        self.curl.write_text(
            "#!/bin/sh\nwhile [ $# -gt 0 ]; do "
            "if [ \"$1\" = --output ]; then shift; "
            f"printf '{content}' > \"$1\"; exit 0; fi; shift; done\n"
        )
        self.curl.chmod(0o755)

    def test_encrypted_artifact_is_uploaded(self) -> None:
        self.write_fake_curl("age-encryption.org/v1\\nexample")
        result = self.run_backup()
        self.assertEqual(result.returncode, 0, result.stderr)
        artifact = Path(self.output.read_text().strip().split("=", 1)[1])
        self.assertTrue(artifact.read_bytes().startswith(b"age-encryption.org/v1"))

    def test_plaintext_is_rejected(self) -> None:
        self.write_fake_curl("PGDMPplaintext")
        result = self.run_backup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("age-encrypted", result.stderr)
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob("*.age")))

    def test_failed_export_is_not_uploaded(self) -> None:
        self.curl.write_text("#!/bin/sh\nexit 22\n")
        self.curl.chmod(0o755)
        result = self.run_backup()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
