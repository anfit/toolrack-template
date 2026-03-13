# toolrack-template

Starter repository for a personal or team scripts collection powered by
`toolrack`.

This template is the companion repo to
[`toolrack`](https://github.com/anfit/toolrack), the dispatcher engine that
turns a scripts folder plus sidecars into a typed CLI.

## Why This Exists

AI makes it much easier to write simple scripts than it used to. That is great
right up until your "quick helpers" become a private archaeological site.

This template exists because:

- AI lowers the cost of writing small scripts.
- A larger script collection increases the need for clear organization,
  consistent interfaces, and lightweight documentation.
- AI works best with compartmentalized tasks, so small focused scripts are a
  feature, not a temporary phase.
- AI output is not deterministic, and your future self deserves at least some
  automation that does the same thing twice in a row without improvising.

In other words: let the model help you write the little tools, then let the
repo help you keep them from becoming a drawer full of mystery adapters.

## What This Template Includes

- `scripts/`: your runnable scripts
- `.toolrack`: registry of scripts exposed in the CLI
- `bin/your-tools` and `bin/your-tools.cmd`: wrapper templates
- `setup_toolrack.py`: guided bootstrap for the local virtualenv and wrappers
- `sync_toolrack.py`: refresh selected template-maintained files from the canonical repo
- `AGENTS.md`: contributor guidance for adding scripts, sidecars, tests, and docs
- `scripts/example/hello.py` + `hello.yml`: minimal sample command
- `scripts/example/README.md`: example group-level documentation

The example script is only a sample. The repository contract is the generic
one above: any supported script can live under `scripts/` with an adjacent
sidecar.

Contributor guidance for shaping new commands lives in [AGENTS.md](AGENTS.md).

## First-Time Setup

Recommended flow:

```powershell
python .\setup_toolrack.py
```

The setup script will:

- ask for the CLI command name you want in `bin/`
- ask where your `toolrack` checkout lives
- create `.venv/` if needed
- install `toolrack` into that virtualenv
- generate `bin/<your-command>` and `bin/<your-command>.cmd`
- add `bin/` to `~/.bashrc`
- add `bin/` to Cygwin's `.bashrc` when a Cygwin home is detected
- attempt to install Bash completion files under `~/.bash_completion.d`
- add a small loader block to `.bashrc` so those completion files are sourced

Non-interactive usage is also supported:

```powershell
python .\setup_toolrack.py --yes --cli-name my-tools --toolrack ..\toolrack
```

After setup, open a new shell and run your generated command:

```powershell
my-tools --help
my-tools example hello --name Alice
```

If completion was configured successfully, Bash and Cygwin Bash should also
offer tab completion for your generated command after you open a new shell.

## Syncing Template-Maintained Files

Some files in a working scripts repo may intentionally track the canonical
`toolrack-template` repository over time. To refresh those files in place
without creating commits automatically, run:

```powershell
python .\sync_toolrack.py
```

Or preview changes first:

```powershell
python .\sync_toolrack.py --dry-run
```

The sync script updates a fixed set of template-owned files such as
`SIDECAR_SPEC.md`, `AGENTS.md`, `setup_toolrack.py`, and the template test
files.

## Repository Contract

- Registry file: `.toolrack`
- Scripts root: `scripts/`
- Wrapper scripts set `TOOLRACK_CLI_NAME`, `TOOLRACK_REPO_ROOT`,
  `TOOLRACK_SCRIPTS_ROOT`, and `TOOLRACK_REGISTRY_FILE`
- The wrapper filename becomes the visible CLI command name

For the sidecar format, see [SIDECAR_SPEC.md](SIDECAR_SPEC.md).
For the engine behind this template, see
[`toolrack`](https://github.com/anfit/toolrack).
