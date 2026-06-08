#!/usr/bin/env python
"""Enforce changelog updates when hiddenimports change in ctrx_backend.spec."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def _resolve_base(base_ref: str, cwd: Path) -> str:
    probe = _run_git(["rev-parse", "--verify", base_ref], cwd)
    if probe.returncode == 0:
        return base_ref
    fallback = _run_git(["rev-parse", "--verify", "HEAD~1"], cwd)
    if fallback.returncode == 0:
        print(
            f"[warn] Base '{base_ref}' not found, falling back to HEAD~1 for diff.",
            file=sys.stderr,
        )
        return "HEAD~1"
    print(
        f"[warn] Base '{base_ref}' and HEAD~1 both unavailable; skip policy gate.",
        file=sys.stderr,
    )
    return ""


def _file_changed(base: str, file_path: str, cwd: Path) -> bool:
    if not base:
        return False
    result = _run_git(["diff", "--name-only", base, "--", file_path], cwd)
    if result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        return False
    return bool(result.stdout.strip())


def _hiddenimports_changed(base: str, spec_path: str, cwd: Path) -> bool:
    if not base:
        return False
    result = _run_git(["diff", "-U0", base, "--", spec_path], cwd)
    if result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        return False
    watched_tokens = (
        "common_hidden",
        "windows_hidden",
        "linux_hidden",
        "hiddenimports",
    )
    return any(token in result.stdout for token in watched_tokens)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, help="Base ref to compare, e.g. origin/master")
    parser.add_argument("--spec", required=True, help="Spec file path")
    parser.add_argument("--changelog", required=True, help="Hiddenimports changelog path")
    args = parser.parse_args()

    repo_root = Path.cwd()
    base = _resolve_base(args.base, repo_root)
    hidden_changed = _hiddenimports_changed(base, args.spec, repo_root)
    changelog_changed = _file_changed(base, args.changelog, repo_root)

    if hidden_changed and not changelog_changed:
        print(
            "hiddenimports changed in spec but changelog was not updated: "
            f"{args.changelog}",
            file=sys.stderr,
        )
        return 1

    print("hiddenimports gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
