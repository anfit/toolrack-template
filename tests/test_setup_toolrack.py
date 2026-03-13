from __future__ import annotations

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
            (bin_dir / "your-tools").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            (bin_dir / "your-tools.cmd").write_text("@echo off\r\n", encoding="utf-8")

            with mock.patch.object(setup_toolrack, "BIN_DIR", bin_dir):
                targets = setup_toolrack.write_wrappers("my-tools", force=False)

            self.assertTrue(targets["posix"].is_file())
            self.assertTrue(targets["cmd"].is_file())
            self.assertEqual("#!/usr/bin/env bash\n", targets["posix"].read_text(encoding="utf-8"))
            self.assertTrue(targets["cmd"].read_text(encoding="utf-8").startswith("@echo off"))

    def test_build_options_uses_defaults_with_yes(self):
        with tempfile.TemporaryDirectory() as tmp:
            toolrack = Path(tmp) / "toolrack"
            (toolrack / "src" / "toolrack").mkdir(parents=True)
            (toolrack / "src" / "toolrack" / "cli.py").write_text("", encoding="utf-8")

            with mock.patch.object(setup_toolrack, "default_toolrack_path", return_value=toolrack):
                with mock.patch.object(setup_toolrack, "default_cli_name", return_value="repo-tools"):
                    args = setup_toolrack.parse_args(["--yes"])
                    options = setup_toolrack.build_options(args)

            self.assertEqual("repo-tools", options.cli_name)
            self.assertEqual(toolrack.resolve(), options.toolrack_path)

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
        self.assertEqual(f"/cygdrive/{drive}{suffix}", path)


if __name__ == "__main__":
    unittest.main()
