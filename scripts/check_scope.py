#!/usr/bin/env python3
"""Puerta de integración: comprueba que un cambio solo tocó los archivos permitidos."""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path


def run_cmd(args: list[str]) -> tuple[int, str, str]:
    """Ejecuta un comando sin shell y devuelve (código, stdout, stderr)."""
    try:
        done = subprocess.run(
            args,
            capture_output=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, "", str(error)
    return (done.returncode, done.stdout.decode("utf-8", "surrogateescape"),
            done.stderr.decode("utf-8", "surrogateescape"))


def git(repo: Path, *args: str) -> tuple[int, str, str]:
    """Corre git dentro del repositorio indicado."""
    return run_cmd(["git", "-C", str(repo), *args])


def fail(message: str) -> int:
    """Informa el error como JSON y por stderr, y devuelve el código de uso inválido."""
    json.dump({"error": message}, sys.stdout, ensure_ascii=True)
    sys.stdout.write("\n")
    sys.stderr.write(message + "\n")
    return 2


def changed_files(repo: Path, base: str) -> tuple[int, list[str]]:
    """Lista los archivos cambiados respecto a base más los no rastreados, con barras."""
    code, out, err = git(repo, "diff", "--name-only", "-z", base)
    if code != 0:
        return code, []
    code, others, err = git(repo, "ls-files", "--others", "--exclude-standard", "-z")
    if code != 0:
        return code, []
    names = [name for name in out.split("\0") if name]
    names += [name for name in others.split("\0") if name]
    return 0, sorted({name.replace("\\", "/") for name in names})


def main(argv: list[str] | None = None) -> int:
    """Compara los archivos cambiados con los globs permitidos."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True, help="raíz del repositorio git")
    parser.add_argument(
        "--allowed",
        action="append",
        required=True,
        metavar="GLOB",
        help="patrón permitido, relativo a la raíz y con / (repetible)",
    )
    parser.add_argument("--base", default="HEAD", help="referencia base del diff (por omisión HEAD)")
    args = parser.parse_args(argv)

    code, changed = changed_files(args.repo, args.base)
    if code != 0:
        return fail(f"no es un repositorio git o la base {args.base} no existe")

    patterns = [pattern.replace("\\", "/") for pattern in args.allowed]
    outside = [
        path
        for path in changed
        if not any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)
    ]
    result = {"ok": not outside, "changed": changed, "outside": outside}
    json.dump(result, sys.stdout, ensure_ascii=True)
    sys.stdout.write("\n")
    return 0 if not outside else 1


if __name__ == "__main__":
    raise SystemExit(main())
