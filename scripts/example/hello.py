#!/usr/bin/env python3
import argparse


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    print(f"hello, {args.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
