# toolrack-template

Starter repository for a personal or team scripts collection powered by
`toolrack`.

## What This Template Includes

- `scripts/`: your runnable scripts
- `.toolrack`: registry of scripts exposed in the CLI
- `bin/your-tools` and `bin/your-tools.cmd`: wrapper templates
- `setup_toolrack.py`: guided bootstrap for the local virtualenv and wrappers
- `scripts/example/hello.py` + `hello.yml`: minimal sample command

The example script is only a sample. The repository contract is the generic
one above: any supported script can live under `scripts/` with an adjacent
sidecar.

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

Non-interactive usage is also supported:

```powershell
python .\setup_toolrack.py --yes --cli-name my-tools --toolrack ..\toolrack
```

After setup, open a new shell and run your generated command:

```powershell
my-tools --help
my-tools example hello --name Alice
```

## Repository Contract

- Registry file: `.toolrack`
- Scripts root: `scripts/`
- Wrapper scripts set `TOOLRACK_CLI_NAME`, `TOOLRACK_REPO_ROOT`,
  `TOOLRACK_SCRIPTS_ROOT`, and `TOOLRACK_REGISTRY_FILE`
- The wrapper filename becomes the visible CLI command name

For the sidecar format, see [SIDECAR_SPEC.md](SIDECAR_SPEC.md).
