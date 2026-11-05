#!/usr/bin/env python3
"""Interactive bootstrap for a toolrack-based scripts repository."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
BIN_DIR = REPO_ROOT / "bin"
DEFAULT_WRAPPER_BASENAME = "your-tools"
PYPI_PACKAGE = "toolrack-cli"
LEGACY_PACKAGE = "toolrack"
PATH_BLOCK_MARKER = "toolrack-template bin"
COMPLETION_BLOCK_MARKER = "toolrack-template bash completion loader"
LEGACY_COMPLETION_BLOCK_MARKER = "toolrack-template completion"


@dataclass
class SetupOptions:
    cli_name: str
    toolrack_path: Path | None
    python_executable: str
    force: bool = False
    remove_template_assets: bool = False


def default_cli_name() -> str:
    raw = REPO_ROOT.name.strip().replace("_", "-")
    return raw or DEFAULT_WRAPPER_BASENAME


def validate_cli_name(value: str) -> str:
    name = value.strip()
    if not name:
        raise ValueError("CLI name cannot be empty.")
    if any(sep in name for sep in ("/", "\\", os.pathsep)):
        raise ValueError("CLI name must be a bare command name, not a path.")
    if name in {".", ".."}:
        raise ValueError("CLI name must not be '.' or '..'.")
    return name


def validate_toolrack_path(value: str | Path) -> Path:
    path = Path(value).expanduser().resolve()
    marker = path / "src" / "toolrack" / "cli.py"
    if not marker.is_file():
        raise ValueError(f"toolrack checkout not found at {path}")
    return path


def venv_python(repo_root: Path) -> Path:
    if os.name == "nt":
        return repo_root / ".venv" / "Scripts" / "python.exe"
    return repo_root / ".venv" / "bin" / "python"


def prompt_with_default(prompt: str, default: str) -> str:
    value = input(f"{prompt} [{default}]: ").strip()
    return value or default


def resolve_python_executable(python_executable: str) -> str:
    candidates: list[str] = []
    for candidate in (
        python_executable,
        getattr(sys, "_base_executable", None),
        sys.executable,
    ):
        if not candidate:
            continue
        if candidate not in candidates:
            candidates.append(candidate)

    for candidate in candidates:
        path = Path(candidate)
        if path.is_file():
            return str(path)

    return python_executable


def interpreter_works(python_path: Path) -> bool:
    try:
        result = subprocess.run(
            [str(python_path), "-c", "import sys; print(sys.executable)"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


def ensure_virtualenv(python_executable: str, repo_root: Path) -> Path:
    python_path = venv_python(repo_root)
    base_python = resolve_python_executable(python_executable)

    if python_path.is_file() and interpreter_works(python_path):
        return python_path

    if (repo_root / ".venv").exists():
        shutil.rmtree(repo_root / ".venv")

    subprocess.run(
        [base_python, "-m", "venv", str(repo_root / ".venv")],
        check=True,
    )

    if not interpreter_works(python_path):
        raise RuntimeError(f"virtualenv interpreter is not usable: {python_path}")

    return python_path


def install_toolrack(python_path: Path, toolrack_path: Path | None = None) -> None:
    """Install the engine from PyPI, or editable from a local checkout."""
    # Before the PyPI release the engine was an editable install under the
    # distribution name "toolrack". It ships the same import package as
    # toolrack-cli, so a leftover copy would shadow the new install.
    subprocess.run(
        [str(python_path), "-m", "pip", "uninstall", "-y", LEGACY_PACKAGE],
        check=False,
        capture_output=True,
    )
    if toolrack_path is None:
        command = [str(python_path), "-m", "pip", "install", "--upgrade", PYPI_PACKAGE]
    else:
        command = [str(python_path), "-m", "pip", "install", "-e", str(toolrack_path)]
    subprocess.run(command, check=True)


def wrapper_targets(cli_name: str) -> dict[str, Path]:
    return {
        "posix": BIN_DIR / cli_name,
        "cmd": BIN_DIR / f"{cli_name}.cmd",
    }


def wrapper_templates() -> dict[str, Path]:
    return {
        "posix": BIN_DIR / DEFAULT_WRAPPER_BASENAME,
        "cmd": BIN_DIR / f"{DEFAULT_WRAPPER_BASENAME}.cmd",
    }


# Built-in copies of bin/your-tools and bin/your-tools.cmd. A repository that was
# set up with --remove-template-assets (or predates the template wrappers) has no
# template files to copy, so setup falls back to these. A test keeps them
# identical to the files in bin/.
FALLBACK_WRAPPERS = {
    "posix": """\
#!/bin/bash
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
if [[ "$SCRIPT_PATH" != */* ]]; then
  SCRIPT_PATH="./$SCRIPT_PATH"
fi
SCRIPT_DIR="${SCRIPT_PATH%/*}"
if [[ "$SCRIPT_DIR" == "$SCRIPT_PATH" ]]; then
  SCRIPT_DIR="."
fi
SCRIPT_DIR="$(cd -- "$SCRIPT_DIR" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

export TOOLRACK_CLI_NAME="${BASH_SOURCE[0]##*/}"
export TOOLRACK_REPO_ROOT="$REPO_ROOT"
export TOOLRACK_SCRIPTS_ROOT="$REPO_ROOT/scripts"
export TOOLRACK_REGISTRY_FILE="$REPO_ROOT/.toolrack"

# Windows venvs use Scripts/, POSIX venvs use bin/.
if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
  PYTHON="$REPO_ROOT/.venv/bin/python"
else
  PYTHON="$REPO_ROOT/.venv/Scripts/python.exe"
fi

exec "$PYTHON" -m toolrack "$@"
""",
    "cmd": """\
@echo off
setlocal

set "REPO_ROOT=%~dp0.."
for %%I in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fI"

set "TOOLRACK_CLI_NAME=%~n0"
set "TOOLRACK_REPO_ROOT=%REPO_ROOT%"
set "TOOLRACK_SCRIPTS_ROOT=%REPO_ROOT%\\scripts"
set "TOOLRACK_REGISTRY_FILE=%REPO_ROOT%\\.toolrack"

"%REPO_ROOT%\\.venv\\Scripts\\python.exe" -m toolrack %*
""",
}


def wrapper_template_text(kind: str) -> str:
    """Wrapper template contents (LF newlines): the file in bin/, else the built-in copy."""
    template = wrapper_templates()[kind]
    if template.is_file():
        text = template.read_text(encoding="utf-8")
    else:
        text = FALLBACK_WRAPPERS[kind]
    return text.replace("\r\n", "\n").replace("\r", "\n")


def write_wrappers(cli_name: str, force: bool) -> dict[str, Path]:
    targets = wrapper_targets(cli_name)

    for kind, target in targets.items():
        if target.exists() and not force:
            raise FileExistsError(f"{target} already exists. Re-run with --force to overwrite it.")
    BIN_DIR.mkdir(parents=True, exist_ok=True)

    for kind, target in targets.items():
        contents = wrapper_template_text(kind)
        if kind == "posix":
            # Force LF line endings so the shebang stays portable in Git Bash and Cygwin.
            target.write_text(contents, encoding="utf-8", newline="\n")
            if os.name != "nt":
                target.chmod(target.stat().st_mode | 0o111)
        else:
            target.write_text(contents, encoding="utf-8", newline="\r\n")
    return targets


def bash_path_for(path: Path, *, style: str) -> str:
    resolved = path.resolve()
    posix = resolved.as_posix()

    if style == "posix":
        return posix

    drive = resolved.drive.rstrip(":").lower()
    if not drive:
        return posix

    suffix = posix[len(resolved.drive) :]
    if style == "git-bash":
        return f"/{drive}{suffix}"
    if style == "cygwin":
        return f"/cygdrive/{drive}{suffix}"
    raise ValueError(f"unsupported bash path style: {style}")


def append_path_block(bashrc_path: Path, bin_dir: Path, *, style: str) -> bool:
    bash_path = bash_path_for(bin_dir, style=style)
    block = (
        f"\n# Added by setup_toolrack.py ({PATH_BLOCK_MARKER})\n"
        f'export PATH="{bash_path}:$PATH"\n'
    )
    existing = bashrc_path.read_text(encoding="utf-8") if bashrc_path.exists() else ""
    if PATH_BLOCK_MARKER in existing or f'export PATH="{bash_path}:$PATH"' in existing:
        return False

    if existing and not existing.endswith("\n"):
        existing += "\n"

    bashrc_path.parent.mkdir(parents=True, exist_ok=True)
    # Force LF line endings so .bashrc stays portable across Git Bash and Cygwin.
    with bashrc_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(existing + block)
    return True


def append_completion_block(bashrc_path: Path) -> bool:
    def _strip_legacy_completion_blocks(text: str) -> str:
        lines = text.splitlines(keepends=True)
        cleaned: list[str] = []
        skip = False
        for line in lines:
            if f"({LEGACY_COMPLETION_BLOCK_MARKER})" in line:
                skip = True
                continue
            if skip:
                if line.strip() == "fi":
                    skip = False
                continue
            cleaned.append(line)
        return "".join(cleaned)

    block = (
        f"\n# Added by setup_toolrack.py ({COMPLETION_BLOCK_MARKER})\n"
        'if [ -d ~/.bash_completion.d ]; then\n'
        '  for f in ~/.bash_completion.d/*; do\n'
        '    [ -r "$f" ] && . "$f"\n'
        "  done\n"
        "fi\n"
    )
    existing = bashrc_path.read_text(encoding="utf-8") if bashrc_path.exists() else ""
    existing = _strip_legacy_completion_blocks(existing)
    if COMPLETION_BLOCK_MARKER in existing or "for f in ~/.bash_completion.d/*;" in existing:
        return False

    if existing and not existing.endswith("\n"):
        existing += "\n"

    bashrc_path.parent.mkdir(parents=True, exist_ok=True)
    with bashrc_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(existing + block)
    return True


def write_completion_script(
    completion_dir: Path,
    python_path: Path,
    cli_name: str,
    *,
    force: bool = False,
) -> Path:
    completion_dir.mkdir(parents=True, exist_ok=True)
    target = completion_dir / cli_name
    if target.exists() and not force:
        return target

    env = os.environ.copy()
    env.update(
        {
            "TOOLRACK_CLI_NAME": cli_name,
            "TOOLRACK_REPO_ROOT": str(REPO_ROOT),
            "TOOLRACK_SCRIPTS_ROOT": str(REPO_ROOT / "scripts"),
            "TOOLRACK_REGISTRY_FILE": str(REPO_ROOT / ".toolrack"),
        }
    )
    result = subprocess.run(
        [str(python_path), "-m", "toolrack", "core", "install-completion", "bash"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    target.write_text(
        result.stdout.replace("\r\n", "\n").replace("\r", "\n"),
        encoding="utf-8",
        newline="\n",
    )
    return target


def cleanup_template_assets(cli_name: str) -> dict[str, list[str]]:
    removed: list[str] = []
    skipped: list[str] = []

    metadata_files = [
        REPO_ROOT / ".toolrack",
        REPO_ROOT / ".toolrack.cache.json",
    ]
    example_files = [
        REPO_ROOT / "scripts" / "example" / "hello.py",
        REPO_ROOT / "scripts" / "example" / "hello.yml",
        REPO_ROOT / "scripts" / "example" / "README.md",
    ]

    registry_path = metadata_files[0]
    if registry_path.exists():
        contents = [
            line for line in registry_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and line.strip() != "scripts/example/hello.py"
        ]
        registry_path.write_text(
            ("\n".join(contents) + "\n") if contents else "",
            encoding="utf-8",
            newline="\n",
        )

    for path in example_files:
        if path.exists():
            path.unlink()
            removed.append(path.relative_to(REPO_ROOT).as_posix())

    cache_path = metadata_files[1]
    if cache_path.exists():
        cache_path.unlink()
        removed.append(cache_path.relative_to(REPO_ROOT).as_posix())

    example_dir = REPO_ROOT / "scripts" / "example"
    if example_dir.exists() and not any(example_dir.iterdir()):
        example_dir.rmdir()

    template_wrappers = [BIN_DIR / DEFAULT_WRAPPER_BASENAME, BIN_DIR / f"{DEFAULT_WRAPPER_BASENAME}.cmd"]
    if cli_name == DEFAULT_WRAPPER_BASENAME:
        skipped.extend(path.relative_to(REPO_ROOT).as_posix() for path in template_wrappers)
    else:
        for path in template_wrappers:
            if path.exists():
                path.unlink()
                removed.append(path.relative_to(REPO_ROOT).as_posix())

    return {"removed": removed, "skipped": skipped}


def find_cygwin_bashrc(home_dir: Path | None = None) -> Path | None:
    username = os.environ.get("USERNAME") or os.environ.get("USER")
    if not username:
        return None

    candidates: list[Path] = []
    if home_dir is not None:
        candidates.append(home_dir / ".bashrc")

    system_drive = Path(os.environ.get("SystemDrive", "C:") + "\\")
    for root in (
        system_drive / "cygwin64",
        system_drive / "cygwin",
        Path("C:/tools/cygwin"),
        Path("C:/tools/cygwin64"),
    ):
        candidates.append(root / "home" / username / ".bashrc")

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def configure_shell_init(bin_dir: Path, python_path: Path, cli_name: str, force: bool) -> dict[str, str]:
    updates: dict[str, str] = {}

    home_bashrc = Path.home() / ".bashrc"
    if append_path_block(home_bashrc, bin_dir, style="git-bash"):
        updates["bashrc"] = str(home_bashrc)
    if append_completion_block(home_bashrc):
        updates["bash_completion_loader"] = str(home_bashrc)
    bash_completion = write_completion_script(
        Path.home() / ".bash_completion.d",
        python_path,
        cli_name,
        force=force,
    )
    updates["bash_completion"] = str(bash_completion)

    cygwin_bashrc = find_cygwin_bashrc()
    if cygwin_bashrc and cygwin_bashrc != home_bashrc:
        if append_path_block(cygwin_bashrc, bin_dir, style="cygwin"):
            updates["cygwin_bashrc"] = str(cygwin_bashrc)
        if append_completion_block(cygwin_bashrc):
            updates["cygwin_completion_loader"] = str(cygwin_bashrc)
        cygwin_completion = write_completion_script(
            cygwin_bashrc.parent / ".bash_completion.d",
            python_path,
            cli_name,
            force=force,
        )
        updates["cygwin_completion"] = str(cygwin_completion)

    return updates


def run_setup(options: SetupOptions) -> dict[str, str]:
    python_path = ensure_virtualenv(options.python_executable, REPO_ROOT)
    install_toolrack(python_path, options.toolrack_path)
    targets = write_wrappers(options.cli_name, options.force)
    result = {
        "python": str(python_path),
        "toolrack": str(options.toolrack_path) if options.toolrack_path else f"{PYPI_PACKAGE} (PyPI)",
        "posix_wrapper": str(targets["posix"]),
        "cmd_wrapper": str(targets["cmd"]),
    }
    result.update(configure_shell_init(BIN_DIR, python_path, options.cli_name, options.force))
    if options.remove_template_assets:
        cleanup = cleanup_template_assets(options.cli_name)
        result["removed_template_assets"] = "\n".join(cleanup["removed"])
        result["skipped_template_assets"] = "\n".join(cleanup["skipped"])
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli-name", help="Command name to create in bin/.")
    parser.add_argument(
        "--toolrack",
        help=f"Developer override: editable-install this local toolrack checkout instead of {PYPI_PACKAGE} from PyPI.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python interpreter used to create .venv (default: current interpreter).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing generated wrapper files.",
    )
    parser.add_argument(
        "--remove-template-assets",
        action="store_true",
        help="Remove the example command and template wrappers after setup.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Use defaults for any value not provided on the command line.",
    )
    return parser.parse_args(argv)


def build_options(args: argparse.Namespace) -> SetupOptions:
    cli_default = default_cli_name()

    cli_name = args.cli_name
    if not args.yes and not cli_name:
        cli_name = prompt_with_default("CLI command name", cli_default)

    cli_name = validate_cli_name(cli_name or cli_default)
    toolrack_path = validate_toolrack_path(args.toolrack) if args.toolrack else None

    return SetupOptions(
        cli_name=cli_name,
        toolrack_path=toolrack_path,
        python_executable=args.python,
        force=args.force,
        remove_template_assets=args.remove_template_assets,
    )


def print_summary(options: SetupOptions, result: dict[str, str]) -> None:
    path_lines = []
    if "bashrc" in result:
        path_lines.append(f"Bash PATH updated: {result['bashrc']}")
    if "cygwin_bashrc" in result:
        path_lines.append(f"Cygwin PATH updated: {result['cygwin_bashrc']}")
    if not path_lines:
        path_lines.append(f"Add {BIN_DIR} to PATH.")

    completion_lines = []
    if "bash_completion_loader" in result:
        completion_lines.append(f"Bash completion loader updated: {result['bash_completion_loader']}")
    if "bash_completion" in result:
        completion_lines.append(f"Bash completion script: {result['bash_completion']}")
    if "cygwin_completion_loader" in result:
        completion_lines.append(f"Cygwin completion loader updated: {result['cygwin_completion_loader']}")
    if "cygwin_completion" in result:
        completion_lines.append(f"Cygwin completion script: {result['cygwin_completion']}")
    if not completion_lines:
        completion_lines.append("Bash completion was not configured automatically.")

    cleanup_lines = []
    if result.get("removed_template_assets"):
        cleanup_lines.append("Removed template assets:")
        cleanup_lines.extend(f"  {line}" for line in result["removed_template_assets"].splitlines())
    if result.get("skipped_template_assets"):
        cleanup_lines.append("Kept template assets:")
        cleanup_lines.extend(
            f"  {line}  (kept because your CLI name is '{DEFAULT_WRAPPER_BASENAME}')"
            for line in result["skipped_template_assets"].splitlines()
        )

    path_note = "\n".join(
        [
            *path_lines,
            *completion_lines,
            *cleanup_lines,
            f"Then run `{options.cli_name} --help`.",
            f"Windows wrapper: {result['cmd_wrapper']}",
            f"POSIX wrapper:   {result['posix_wrapper']}",
        ]
    )
    print(path_note)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        options = build_options(args)
        result = run_setup(options)
    except (FileExistsError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"setup-toolrack: {exc}", file=sys.stderr)
        return 1

    print_summary(options, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
