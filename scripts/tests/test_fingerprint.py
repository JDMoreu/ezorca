from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fingerprint  # noqa: E402

SCRIPT = Path(__file__).resolve().parents[1] / "fingerprint.py"


def git(repo: Path, *args: str) -> str:
    """Corre git en el repo temporal y devuelve su stdout."""
    done = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )
    return done.stdout.strip()


class FingerprintTests(unittest.TestCase):
    """Cubre huella estable, contenido no rastreado, --extra y repos inválidos."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "Test")
        (self.repo / "a.txt").write_text("a\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "init")

    def run_fp(self, *extra: str) -> tuple[int, str]:
        """Ejecuta main y devuelve código y stdout."""
        out = io.StringIO()
        argv = ["--repo", str(self.repo), *extra]
        with redirect_stdout(out):
            code = fingerprint.main(argv)
        return code, out.getvalue()

    def test_untracked_content_changes_fingerprint(self) -> None:
        new = self.repo / "nuevo.txt"
        new.write_text("uno", encoding="utf-8")
        first_code, first_out = self.run_fp()
        first = json.loads(first_out)
        new.write_text("dos", encoding="utf-8")
        second_code, second_out = self.run_fp()
        second = json.loads(second_out)
        self.assertEqual(first_code, 0)
        self.assertEqual(second_code, 0)
        self.assertNotEqual(first["fingerprint"], second["fingerprint"])
        self.assertEqual(first["untracked"], ["nuevo.txt"])
        self.assertTrue(first["dirty"])
        self.assertEqual(first["head"], git(self.repo, "rev-parse", "HEAD"))

    def test_run_cmd_keeps_raw_bytes(self) -> None:
        code, out, _ = fingerprint.run_cmd([sys.executable, "-c", "import sys; sys.stdout.buffer.write(bytes([13,10]))"])
        self.assertEqual(out, b"\r\n")

    def test_diff_preserves_line_endings(self) -> None:
        git(self.repo, "config", "core.autocrlf", "false")
        path = self.repo / "a.txt"
        path.write_bytes(b"changed\n")
        first = json.loads(self.run_fp()[1])["fingerprint"]
        path.write_bytes(b"changed\r\n")
        self.assertNotEqual(first, json.loads(self.run_fp()[1])["fingerprint"])

    def test_stable_without_changes(self) -> None:
        first_code, first_out = self.run_fp()
        second_code, second_out = self.run_fp()
        self.assertEqual((first_code, second_code), (0, 0))
        first = json.loads(first_out)
        self.assertEqual(first, json.loads(second_out))
        self.assertFalse(first["dirty"])
        self.assertEqual(first["untracked"], [])
        self.assertTrue(first["fingerprint"].startswith("sha256:"))

    def test_extra_content_is_covered(self) -> None:
        extra = self.root / "outside.md"
        extra.write_text("uno", encoding="utf-8")
        first_code, first_out = self.run_fp("--extra", str(extra))
        extra.write_text("dos", encoding="utf-8")
        second_code, second_out = self.run_fp("--extra", str(extra))
        self.assertEqual((first_code, second_code), (0, 0))
        self.assertNotEqual(
            json.loads(first_out)["fingerprint"], json.loads(second_out)["fingerprint"]
        )
        self.assertEqual(json.loads(first_out)["extra"], [str(extra)])

    def test_missing_extra_exits_2(self) -> None:
        code, _ = self.run_fp("--extra", str(self.root / "no-existe.md"))
        self.assertEqual(code, 2)

    def test_not_a_git_repo_exits_2(self) -> None:
        plain = self.root / "plain"
        plain.mkdir()
        out = io.StringIO()
        with redirect_stdout(out):
            code = fingerprint.main(["--repo", str(plain)])
        self.assertEqual(code, 2)

    def test_help_exits_0(self) -> None:
        done = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True)
        self.assertEqual(done.returncode, 0)


if __name__ == "__main__":
    unittest.main()
