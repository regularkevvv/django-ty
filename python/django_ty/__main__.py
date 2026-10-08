"""Run ty with one of django-ty's packaged backends, or print its configuration."""

from __future__ import annotations

import argparse
import os
import shutil

from .runtime import checker_options, config_overrides


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", choices=("wasm", "monty"), default="wasm")
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
        parser.error("expected check followed by ty options and paths")
    executable = shutil.which("ty")
    if executable is None:
        parser.error("ty is not on PATH; run inside your project's environment")
    os.execv(
        executable,
        [
            executable,
            "check",
            *checker_options(args.runtime, args.settings_module),
            *args.command[1:],
        ],
    )


if __name__ == "__main__":
    main()
