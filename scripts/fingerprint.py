#!/usr/bin/env python3
"""Huella SHA-256 de la versión exacta que se verifica (HEAD, diff y no rastreados)."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def run_cmd(args: list[str]) -> tuple[int, bytes, bytes]:
    """Ejecuta un comando sin shell y devuelve (código, stdout, stderr)."""
    try:
        done = subprocess.run(
            args,
            capture_output=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, b"", str(error).encode()
    return done.returncode, done.stdout, done.stderr


def git(repo: Path, *args: str) -> tuple[int, bytes, bytes]:
    """Corre git dentro del repositorio indicado."""
    return run_cmd(["git", "-C", str(repo), *args])


def fail(message: str) -> int:
    """Informa el error como JSON y por stderr, y devuelve el código de uso inválido."""
    json.dump({"error": message}, sys.stdout, ensure_ascii=True)
    sys.stdout.write("\n")
    sys.stderr.write(message + "\n")
    return 2


def digest(chunks: list[bytes]) -> str:
    """SHA-256 con prefijo de longitud por trozo, para que la concatenación no sea ambigua."""
    hasher = hashlib.sha256()
    for chunk in chunks:
        hasher.update(len(chunk).to_bytes(8, "big"))
        hasher.update(chunk)
    return "sha256:" + hasher.hexdigest()


def untracked_files(repo: Path) -> tuple[int, list[str]]:
    """Lista los archivos no rastreados y no ignorados, en orden alfabético."""
    code, out, _ = git(repo, "ls-files", "--others", "--exclude-standard", "-z")
    names = sorted(name for name in out.decode("utf-8", "surrogateescape").split("\0") if name)
    return code, names


def main(argv: list[str] | None = None) -> int:
    """Calcula e imprime la huella de la versión verificada."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True, help="raíz del repositorio git")
    parser.add_argument(
        "--extra",
        type=Path,
        action="append",
        default=[],
        help="archivo adicional a cubrir (repetible)",
    )
    args = parser.parse_args(argv)

    missing = [str(path) for path in args.extra if not path.is_file()]
    if missing:
        return fail(f"--extra no existe o no es un archivo: {', '.join(missing)}")

    code, head, err = git(args.repo, "rev-parse", "HEAD")
    if code != 0:
        return fail(f"no es un repositorio git con HEAD válido: {err.decode("utf-8", "replace").strip()}")
    code, diff, err = git(args.repo, "diff", "HEAD", "--binary")
    if code != 0:
        return fail(f"git diff falló: {err.decode("utf-8", "replace").strip()}")
    code, untracked = untracked_files(args.repo)
    if code != 0:
        return fail("git ls-files falló")

    chunks = [head.strip(), diff]
    for name in untracked:
        chunks.append(name.encode("utf-8"))
        chunks.append((args.repo / name).read_bytes())
    for path in args.extra:
        chunks.append(str(path).encode("utf-8"))
        chunks.append(path.read_bytes())

    result = {
        "fingerprint": digest(chunks),
        "head": head.decode("utf-8").strip(),
        "dirty": bool(diff.strip() or untracked),
        "untracked": untracked,
        "extra": [str(path) for path in args.extra],
    }
    json.dump(result, sys.stdout, ensure_ascii=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
