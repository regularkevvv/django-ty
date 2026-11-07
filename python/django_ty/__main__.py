"""Run the Monty companion with Django semantics, or print its configuration."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

from ty_extended import find_ty_extended_bin

from .runtime import checker_options, config_overrides


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", choices=("monty",), default="monty")
    parser.add_argument("--print-config", action="store_true")
    parser.add_argument(
        "--settings-module",
        help="Django settings module passed to the explicit plugin entry",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.print_config:
        if args.command:
            parser.error("--print-config does not take a checker command")
        print(
            "\n".join(
                config_overrides(args.runtime, settings_module=args.settings_module)
            )
        )
        return
    if not args.command or args.command[0] != "check":
        parser.error("expected check followed by companion options and paths")
    executable = str(find_ty_extended_bin())
    command = [
        executable,
        "check",
        *checker_options(args.runtime, args.settings_module),
        *args.command[1:],
    ]
    if sys.platform == "win32":
        try:
            completed = subprocess.run(command)
        except KeyboardInterrupt:
            raise SystemExit(2) from None
        raise SystemExit(completed.returncode)
    os.execv(executable, command)


if __name__ == "__main__":
    main()
