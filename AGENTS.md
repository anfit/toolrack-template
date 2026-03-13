# AGENTS.md

This repository is a starter layout for a `toolrack`-powered scripts repo.
Treat it as the working agreement for adding and maintaining commands.

## Adding a New Script

When you add a runnable script under `scripts/`, add the surrounding assets in
the same change:

1. The script itself: `.py`, `.sh`, `.bash`, or `.sql`
2. An adjacent sidecar: `<script>.yml`
3. Tests for the script or the wrapper logic it depends on
4. A short update to the nearest grouping README

Example:

```text
scripts/example/hello.py
scripts/example/hello.yml
scripts/example/README.md
tests/test_example_hello.py
```

Do not add a script without its sidecar. The sidecar is part of the user-facing
CLI contract.

## Group Layout

Each first-level folder under `scripts/` is a command group. Prefer keeping a
`README.md` in that folder once it contains more than one script or serves a
distinct area such as `github/`, `jira/`, `db/`, or `example/`.

Group READMEs should answer:

- what the group is for
- which commands live there
- shared environment variables or credentials
- any conventions specific to that group

## Sidecar Authoring Guidelines

Use sidecars to design the CLI, not just to expose raw script internals.

Prefer:

- named options for values that are easy to forget or mis-order
- descriptive help text in `description`, arg `help`, and `env`
- explicit `choices` when inputs come from a known set
- defaults for optional, common-case values
- positional arguments only when order is natural and obvious

Use positional arguments for:

- one required primary target such as `issue_key` or `path`
- short command shapes where users can guess the order immediately

Prefer options instead of positionals for:

- more than one or two independent values
- values with similar types that are easy to swap accidentally
- optional inputs
- booleans and mode switches
- filters, output formats, limits, dates, and IDs

Good UX examples:

```yaml
description: Show one issue.
args:
  - name: issue_key
    positional: true
    required: true
    help: Jira issue key, for example PROJ-123.
```

```yaml
description: List pull requests.
args:
  - name: repo
    required: true
    help: Repository name.
  - name: state
    choices: [open, closed, merged]
    default: open
    help: Pull request state.
  - name: limit
    type: int
    default: 20
    help: Maximum number of results.
```

Avoid sidecars that merely mirror opaque script parameters such as:

```yaml
args:
  - name: arg1
    positional: true
  - name: arg2
    positional: true
  - name: arg3
    positional: true
```

If the script interface is hard to explain cleanly, improve the script or add a
small wrapper instead of pushing that complexity onto the caller.

## Tests

Every new command should have tests at the most useful level available.

Prefer:

- unit tests for script parsing and helper logic
- tests for sidecar validation or wrapper behavior when relevant
- integration tests only when shell behavior or subprocess wiring matters

If a script talks to a remote system, keep the default tests local and mock the
remote interaction.

## Registration and Discovery

After adding a script and sidecar, register it in `.toolrack` or use:

```bash
your-tools core auto-register
```

Keep `.toolrack` reviewed like source code. It defines what becomes part of the
visible CLI.

`toolrack` also keeps a cache file next to `.toolrack` for faster startup and
completion. It refreshes automatically when registry-level `core` actions run,
and it self-invalidates when registered scripts or sidecars change.

Still, after a larger rewrite or a batch of sidecar edits, prefer making the
state explicit:

```bash
your-tools core refresh-cache
```

Agents should run `core refresh-cache` after rewriting a registered script or
sidecar in a way that changes the CLI surface, especially before validating
completion behavior.
