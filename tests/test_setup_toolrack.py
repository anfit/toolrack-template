from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import setup_toolrack


class SetupToolrackTests(unittest.TestCase):
    @staticmethod
    def _sample_bin_dir() -> Path:
        return (setup_toolrack.REPO_ROOT / "bin").resolve()

    def test_validate_cli_name_rejects_paths(self):
        with self.assertRaises(ValueError):
            setup_toolrack.validate_cli_name("bin/my-tools")

    def test_validate_toolrack_path_requires_cli_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                setup_toolrack.validate_toolrack_path(root)

    def test_write_wrappers_creates_both_launchers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            (bin_dir / "your-tools").write_text(
                "#!/bin/bash\r\n"
                "set -euo pipefail\r\n"
                "\r\n"
                'SCRIPT_PATH="${BASH_SOURCE[0]}"\r\n',
                encoding="utf-8",
                newline="\r\n",
            )
            (bin_dir / "your-tools.cmd").write_text("@echo off\r\n", encoding="utf-8")

            with mock.patch.object(setup_toolrack, "BIN_DIR", bin_dir):
                targets = setup_toolrack.write_wrappers("my-tools", force=False)

            self.assertTrue(targets["posix"].is_file())
            self.assertTrue(targets["cmd"].is_file())
            posix_contents = targets["posix"].read_text(encoding="utf-8")
            self.assertTrue(posix_contents.startswith("#!/bin/bash\n"))
            self.assertIn('SCRIPT_PATH="${BASH_SOURCE[0]}"\n', posix_contents)
            self.assertTrue(targets["cmd"].read_text(encoding="utf-8").startswith("@echo off"))

    def test_build_options_defaults_to_pypi_install_with_yes(self):
        with mock.patch.object(setup_toolrack, "default_cli_name", return_value="repo-tools"):
            args = setup_toolrack.parse_args(["--yes"])
            options = setup_toolrack.build_options(args)

        self.assertEqual("repo-tools", options.cli_name)
        self.assertIsNone(options.toolrack_path)

    def test_build_options_accepts_local_checkout_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            toolrack = Path(tmp) / "toolrack"
            (toolrack / "src" / "toolrack").mkdir(parents=True)
            (toolrack / "src" / "toolrack" / "cli.py").write_text("", encoding="utf-8")

            args = setup_toolrack.parse_args(["--yes", "--cli-name", "x", "--toolrack", str(toolrack)])
            options = setup_toolrack.build_options(args)

        self.assertEqual(toolrack.resolve(), options.toolrack_path)

    def test_install_toolrack_uses_pypi_by_default_and_editable_for_checkout(self):
        python = Path("py")
        with mock.patch.object(setup_toolrack.subprocess, "run") as run:
            setup_toolrack.install_toolrack(python, None)
            setup_toolrack.install_toolrack(python, Path("/src/toolrack"))

        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(["py", "-m", "pip", "uninstall", "-y", "toolrack"], commands[0])
        self.assertEqual(["py", "-m", "pip", "install", "--upgrade", "toolrack-cli"], commands[1])
        self.assertEqual(["py", "-m", "pip", "uninstall", "-y", "toolrack"], commands[2])
        self.assertEqual(["py", "-m", "pip", "install", "-e"], commands[3][:5])

    def test_resolve_python_executable_prefers_existing_file(self):
        resolved = setup_toolrack.resolve_python_executable(sys.executable)
        self.assertEqual(str(Path(sys.executable)), resolved)

    def test_cleanup_template_assets_removes_example_and_template_wrappers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bin_dir = root / "bin"
            example_dir = root / "scripts" / "example"
            bin_dir.mkdir(parents=True)
            example_dir.mkdir(parents=True)
            (root / ".toolrack").write_text("scripts/example/hello.py\n", encoding="utf-8")
            (root / ".toolrack.cache.json").write_text("{}\n", encoding="utf-8")
            (example_dir / "hello.py").write_text("", encoding="utf-8")
            (example_dir / "hello.yml").write_text("", encoding="utf-8")
            (example_dir / "README.md").write_text("", encoding="utf-8")
            (bin_dir / "your-tools").write_text("", encoding="utf-8")
            (bin_dir / "your-tools.cmd").write_text("", encoding="utf-8")

            with mock.patch.object(setup_toolrack, "REPO_ROOT", root):
                with mock.patch.object(setup_toolrack, "BIN_DIR", bin_dir):
                    result = setup_toolrack.cleanup_template_assets("my-tools")

            self.assertFalse((example_dir / "hello.py").exists())
            self.assertFalse((bin_dir / "your-tools").exists())
            self.assertFalse((root / ".toolrack.cache.json").exists())
            self.assertEqual("", (root / ".toolrack").read_text(encoding="utf-8"))
            self.assertIn("scripts/example/hello.py", result["removed"])
            self.assertIn("bin/your-tools", result["removed"])

    def test_cleanup_template_assets_keeps_template_wrapper_when_cli_name_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bin_dir = root / "bin"
            example_dir = root / "scripts" / "example"
            bin_dir.mkdir(parents=True)
            example_dir.mkdir(parents=True)
            (root / ".toolrack").write_text("scripts/example/hello.py\n", encoding="utf-8")
            (root / ".toolrack.cache.json").write_text("{}\n", encoding="utf-8")
            (example_dir / "hello.py").write_text("", encoding="utf-8")
            (example_dir / "hello.yml").write_text("", encoding="utf-8")
            (example_dir / "README.md").write_text("", encoding="utf-8")
            (bin_dir / "your-tools").write_text("", encoding="utf-8")
            (bin_dir / "your-tools.cmd").write_text("", encoding="utf-8")

            with mock.patch.object(setup_toolrack, "REPO_ROOT", root):
                with mock.patch.object(setup_toolrack, "BIN_DIR", bin_dir):
                    result = setup_toolrack.cleanup_template_assets("your-tools")

            self.assertTrue((bin_dir / "your-tools").exists())
            self.assertIn("bin/your-tools", result["skipped"])

    def test_ensure_virtualenv_recreates_broken_existing_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            venv_python = setup_toolrack.venv_python(root)  # .venv/Scripts/python.exe or .venv/bin/python
            venv_python.parent.mkdir(parents=True)
            venv_python.write_text("", encoding="utf-8")

            created = []

            def fake_run(cmd, **kwargs):
                cmd = [str(part) for part in cmd]
                if cmd[1:3] == ["-c", "import sys; print(sys.executable)"]:
                    if created:
                        return subprocess.CompletedProcess(cmd, 0, stdout="ok\n", stderr="")
                    return subprocess.CompletedProcess(cmd, 103, stdout="", stderr="broken\n")
                if cmd[1:3] == ["-m", "venv"]:
                    created.append(cmd[-1])
                    venv_python.parent.mkdir(parents=True, exist_ok=True)
                    venv_python.write_text("ok", encoding="utf-8")
                    return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
                raise AssertionError(f"unexpected command: {cmd}")

            with mock.patch.object(setup_toolrack.subprocess, "run", side_effect=fake_run):
                python_path = setup_toolrack.ensure_virtualenv(sys.executable, root)

            self.assertEqual(venv_python, python_path)
            self.assertEqual([str(root / ".venv")], created)

    def test_append_path_block_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            bashrc = Path(tmp) / ".bashrc"
            bashrc.write_text("# existing\n", encoding="utf-8")
            bin_dir = self._sample_bin_dir()
            expected_path = setup_toolrack.bash_path_for(bin_dir, style="git-bash")

            changed = setup_toolrack.append_path_block(
                bashrc,
                bin_dir,
                style="git-bash",
            )
            changed_again = setup_toolrack.append_path_block(
                bashrc,
                bin_dir,
                style="git-bash",
            )

            contents = bashrc.read_text(encoding="utf-8")
            self.assertTrue(changed)
            self.assertFalse(changed_again)
            self.assertEqual(1, contents.count(setup_toolrack.PATH_BLOCK_MARKER))
            self.assertIn(f'export PATH="{expected_path}:$PATH"', contents)

    def test_append_path_block_writes_lf_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            bashrc = Path(tmp) / ".bashrc"
            bashrc.write_text("# existing\n", encoding="utf-8", newline="\n")

            setup_toolrack.append_path_block(
                bashrc,
                self._sample_bin_dir(),
                style="git-bash",
            )

            contents = bashrc.read_bytes()
            self.assertIn(b"\n# Added by setup_toolrack.py", contents)
            self.assertNotIn(b"\r\n", contents)

    def test_append_completion_block_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            bashrc = Path(tmp) / ".bashrc"
            bashrc.write_text("# existing\n", encoding="utf-8")

            changed = setup_toolrack.append_completion_block(
                bashrc,
            )
            changed_again = setup_toolrack.append_completion_block(
                bashrc,
            )

            contents = bashrc.read_text(encoding="utf-8")
            self.assertTrue(changed)
            self.assertFalse(changed_again)
            self.assertEqual(1, contents.count(setup_toolrack.COMPLETION_BLOCK_MARKER))
            self.assertIn('for f in ~/.bash_completion.d/*; do', contents)

    def test_append_completion_block_writes_lf_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            bashrc = Path(tmp) / ".bashrc"
            bashrc.write_text("# existing\n", encoding="utf-8", newline="\n")

            setup_toolrack.append_completion_block(
                bashrc,
            )

            contents = bashrc.read_bytes()
            self.assertIn(b"\n# Added by setup_toolrack.py", contents)
            self.assertNotIn(b"\r\n", contents)

    def test_append_completion_block_replaces_legacy_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            bashrc = Path(tmp) / ".bashrc"
            bashrc.write_text(
                (
                    "# existing\n"
                    "# Added by setup_toolrack.py (toolrack-template completion)\n"
                    'if [ -x "/old/wrapper" ]; then\n'
                    '  eval "$(\\"/old/wrapper\\" core install-completion bash 2>/dev/null)"\n'
                    "fi\n"
                ),
                encoding="utf-8",
            )

            changed = setup_toolrack.append_completion_block(bashrc)
            contents = bashrc.read_text(encoding="utf-8")

            self.assertTrue(changed)
            self.assertNotIn("toolrack-template completion", contents)
            self.assertIn("toolrack-template bash completion loader", contents)

    def test_write_completion_script_generates_cli_specific_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            completion_dir = Path(tmp) / ".bash_completion.d"

            def fake_run(cmd, **kwargs):
                self.assertEqual(
                    [str(Path(tmp) / "python.exe"), "-m", "toolrack", "core", "install-completion", "bash"],
                    [str(part) for part in cmd],
                )
                self.assertEqual("my-tools", kwargs["env"]["TOOLRACK_CLI_NAME"])
                return subprocess.CompletedProcess(cmd, 0, stdout="_MY_TOOLS_COMPLETE\n", stderr="")

            with mock.patch.object(setup_toolrack.subprocess, "run", side_effect=fake_run):
                target = setup_toolrack.write_completion_script(
                    completion_dir,
                    Path(tmp) / "python.exe",
                    "my-tools",
                )

            self.assertEqual(completion_dir / "my-tools", target)
            self.assertEqual("_MY_TOOLS_COMPLETE\n", target.read_text(encoding="utf-8"))

    def test_find_cygwin_bashrc_prefers_existing_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "cygwin64" / "home" / "alice"
            home.mkdir(parents=True)
            bashrc = home / ".bashrc"
            bashrc.write_text("", encoding="utf-8")

            with mock.patch.dict(
                "os.environ",
                {"USERNAME": "alice", "SystemDrive": str(Path(tmp).anchor).rstrip("\\")},
                clear=False,
            ):
                found = setup_toolrack.find_cygwin_bashrc(Path(tmp) / "cygwin64" / "home" / "alice")

            self.assertEqual(bashrc, found)

    def test_bash_path_for_cygwin_style(self):
        bin_dir = self._sample_bin_dir()
        resolved = bin_dir.resolve()
        drive = resolved.drive.rstrip(":").lower()
        suffix = resolved.as_posix()[len(resolved.drive) :]
        path = setup_toolrack.bash_path_for(bin_dir, style="cygwin")
        if not resolved.drive:  # POSIX hosts have no drive letter; the path is used as is
            self.assertEqual(resolved.as_posix(), path)
        else:
            self.assertEqual(f"/cygdrive/{drive}{suffix}", path)


if __name__ == "__main__":
    unittest.main()
