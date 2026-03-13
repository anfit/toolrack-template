# `example` Group

This folder is the smallest useful example of a `toolrack` command group.

## What Lives Here

- `hello.py`: simple runnable script
- `hello.yml`: sidecar that defines the CLI help and arguments

The command exposed from this group is:

```bash
your-tools example hello --name Alice
```

## How To Use This Group As a Template

When adding another command to this group or copying this pattern into a new
group, add all of the following together:

1. the script
2. the `.yml` sidecar
3. tests
4. a README update

## Parameter Design

`hello` uses `--name` rather than a positional argument on purpose. Both would
work, but the named option scales better once a command grows beyond a toy
example.

As a rule of thumb:

- use a positional argument for the one obvious primary target
- use named options for filters, modes, optional values, and anything easy to mis-order

That keeps `--help` clearer and makes commands easier to remember.
