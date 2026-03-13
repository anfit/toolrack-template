#!/usr/bin/env python3
"""Sync selected template files from the canonical toolrack-template repo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_BASE_URL = "https://raw.githubusercontent.com/anfit/toolrack-template/main"
SYNC_TARGETS = [
    Path("SIDECAR_SPEC.md"),
    Path("AGENTS.md"),
    Path("setup_toolrack.py"),
    Path("tests/conftest.py"),
    Path("tests/test_setup_toolrack.py"),
    Path("sync_toolrack.py"),
]


def fetch_text(url: str) -> str:
    try:
        with urlopen(url) as response:  # noqa: S310 - explicit user-requested HTTP fetch
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset)
    except HTTPError as exc:
        raise RuntimeError(f"{url}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"{url}: {exc.reason}") from exc


def sync_one(base_url: str, relative_path: Path, *, dry_run: bool) -> tuple[str, bool]:
    url = f"{base_url.rstrip('/')}/{relative_path.as_posix()}"
    remote_text = fetch_text(url).replace("\r\n", "\n").replace("\r", "\n")
    local_path = REPO_ROOT / relative_path
    local_text = local_path.read_text(encoding="utf-8") if local_path.exists() else None
    changed = local_text != remote_text
    if changed and not dry_run:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(remote_text, encoding="utf-8", newline="\n")
    return str(relative_path), changed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base raw-content URL to sync from (default: {DEFAULT_BASE_URL}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without overwriting local files.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    changed_paths: list[str] = []

    try:
        for relative_path in SYNC_TARGETS:
            label, changed = sync_one(args.base_url, relative_path, dry_run=args.dry_run)
            status = "UPDATE" if changed else "OK"
            print(f"{status:6} {label}")
            if changed:
                changed_paths.append(label)
    except RuntimeError as exc:
        print(f"sync-toolrack: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"\nWould update {len(changed_paths)} file(s).")
    else:
        print(f"\nUpdated {len(changed_paths)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
