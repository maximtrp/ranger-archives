#!/usr/bin/env python3

import argparse
import subprocess
import sys
from pathlib import Path


def run_to_file(command, output_path):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as stream:
        return_code = subprocess.run(command, stdout=stream).returncode
    if return_code:
        output.unlink(missing_ok=True)
    return return_code


def run_pipeline(first, second):
    with subprocess.Popen(first, stdout=subprocess.PIPE) as source:
        with subprocess.Popen(second, stdin=source.stdout) as destination:
            source.stdout.close()
            destination_code = destination.wait()
        source_code = source.wait()
    return source_code or destination_code


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--stdout")
    parser.add_argument("--pipe", action="store_true")
    parser.add_argument("--cwd")
    parser.add_argument("--mkdir")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    command = args.command
    if command[:1] == ["--"]:
        command = command[1:]

    if args.mkdir:
        Path(args.mkdir).mkdir(parents=True, exist_ok=True)

    if args.stdout:
        return run_to_file(command, args.stdout)
    if args.cwd:
        Path(args.cwd).mkdir(parents=True, exist_ok=True)
        return subprocess.run(command, cwd=args.cwd).returncode
    if args.pipe:
        try:
            separator = command.index("::")
        except ValueError:
            return 2
        return run_pipeline(command[:separator], command[separator + 1 :])
    if command:
        return subprocess.run(command).returncode
    return 2


if __name__ == "__main__":
    sys.exit(main())
