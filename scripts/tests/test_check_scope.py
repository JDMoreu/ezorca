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

import check_scope  # noqa: E402

SCRIPT = Path(__file__).resolve().parents[1] / "check_scope.py"


def git(repo: Path, *args: str) -> str:
    """Corre git en el repo temporal y devuelve su stdout."""
    done = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )
    return done.stdout.strip()


class CheckScopeTests(unittest.TestCase):
    """Cubre archivos fuera de alcance, no rastreados, --base y repos inválidos."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        (self.repo / "src" / "cli").mkdir(parents=True)
        self.allowed_file = self.repo / "src" / "cli" / "state.rs"
        self.allowed_file.write_text("fn state() {}\n", encoding="utf-8")
        self.readme = self.repo / "README.md"
        self.readme.write_text("# readme\n", encoding="utf-8")
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "Test")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "init")

    def run_scope(self, *args: str) -> tuple[int, dict]:
        """Ejecuta main y devuelve código y JSON de stdout."""
        out = io.StringIO()
        argv = ["--repo", str(self.repo), *args]
        with redirect_stdout(out):
            code = check_scope.main(argv)
        return code, json.loads(out.getvalue())

    def test_outside_file_fails(self) -> None:
        self.allowed_file.write_text("fn state() { todo() }\n", encoding="utf-8")
        self.readme.write_text("# cambiado\n", encoding="utf-8")
        code, result = self.run_scope("--allowed", "src/cli/**")
        self.assertEqual(code, 1)
        self.assertFalse(result["ok"])
        self.assertEqual(result["outside"], ["README.md"])
        self.assertEqual(
            result["changed"],
            ["README.md", "src/cli/state.rs"],
        )

    def test_allowed_globs_pass(self) -> None:
        self.allowed_file.write_text("fn state() { todo() }\n", encoding="utf-8")
        self.readme.write_text("# cambiado\n", encoding="utf-8")
        code, result = self.run_scope(
            "--allowed", "src/cli/**", "--allowed", "README.md"
        )
        self.assertEqual(code, 0)
        self.assertTrue(result["ok"])
        self.assertEqual(result["outside"], [])

    def test_unicode_tracked_name(self) -> None:
        path = self.repo / "\u00f1and\u00fa \u00e1.txt"
        path.write_text("initial", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "unicode")
        path.write_text("changed", encoding="utf-8")
        code, result = self.run_scope("--allowed", "*.txt")
        self.assertEqual(code, 0)
        self.assertEqual(result["changed"], [path.name])

    def test_untracked_file_counts(self) -> None:
        (self.repo / "src").mkdir(exist_ok=True)
        (self.repo / "src" / "otro.rs").write_text("fn otro() {}\n", encoding="utf-8")
        code, result = self.run_scope("--allowed", "src/cli/**")
        self.assertEqual(code, 1)
        self.assertEqual(result["outside"], ["src/otro.rs"])

    def test_base_ref_limits_the_diff(self) -> None:
        self.readme.write_text("# segunda\n", encoding="utf-8")
        git(self.repo, "commit", "-q", "-am", "segunda")
        self.allowed_file.write_text("fn state() { mas() }\n", encoding="utf-8")
        code, result = self.run_scope("--allowed", "src/cli/**", "--base", "HEAD")
        self.assertEqual(code, 0)
        self.assertEqual(result["changed"], ["src/cli/state.rs"])
        code, result = self.run_scope("--allowed", "README.md", "--base", "HEAD~1")
        self.assertEqual(code, 1)
        self.assertEqual(result["outside"], ["src/cli/state.rs"])

    def test_not_a_git_repo_exits_2(self) -> None:
        plain = self.root / "plain"
        plain.mkdir()
        out = io.StringIO()
        with redirect_stdout(out):
            code = check_scope.main(
                ["--repo", str(plain), "--allowed", "**"]
            )
        self.assertEqual(code, 2)

    def test_help_exits_0(self) -> None:
        done = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True)
        self.assertEqual(done.returncode, 0)


if __name__ == "__main__":
    unittest.main()
