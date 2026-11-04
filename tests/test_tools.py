"""Tests for the tools in this repository, using the toolrack pytest plugin.

The fixtures come from `toolrack-cli` (`toolrack_project`, `toolrack_repo`, ...).
`toolrack_project` is this repository; each `run()` executes the real CLI.
"""

from __future__ import annotations


def test_registry_and_sidecars_are_valid(toolrack_project):
    # Raises AssertionError listing every problem. Warnings (for example a stale
    # cache after a fresh checkout) do not fail it; use strict=True to be stricter.
    toolrack_project.validate()


def test_example_hello_runs(toolrack_project):
    result = toolrack_project.run("example", "hello", "--name", "Alice").check()
    assert "Alice" in result.stdout
