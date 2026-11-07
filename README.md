# django-ty

`django-ty` adds Django ORM semantics through the **ty-extended Monty companion**.
The companion delegates to unchanged official Astral ty; it is not a fork of the checker.
Django's hooks and static API ship in one universal Python wheel. Consumers do not
build Rust, install WASM artifacts or run a Python worker.

## Install and check

```sh
uv add django-ty
```

Enable installed plugin discovery in your project:

```toml
[tool.ty.plugins]
auto-discover = true
```

```sh
uv run ty-extended check .
```

For an explicit Django settings module:

```sh
uv run python -m django_ty --settings-module project.settings check .
```

The module launcher resolves the installed companion directly, including when its
executable is absent from `PATH`. No installer command, `.ty` directory or file copy is required.

## Editors

Start `ty-extended server` and enable **workspace diagnostics**. Django's project
index needs closed model modules to provide reverse relations and cross-module
queryset annotations. `openFilesOnly` limits those facts in both the former checker
and the companion.

For the official VS Code extension, use a trusted workspace and configure:

```json
{
  "ty.path": ["/absolute/project/.venv/bin/ty-extended"],
  "ty.diagnosticMode": "workspace"
}
```

On Windows, select `.venv/Scripts/ty-extended.exe`. With Neovim 0.11 or later:

```lua
vim.lsp.config("ty", {
  cmd = { "/absolute/project/.venv/bin/ty-extended", "server" },
  settings = { ty = { diagnosticMode = "workspace" } },
})
vim.lsp.enable("ty")
```

## Versions and migration

Django-ty 0.6.0 requires `ty-extended>=0.87.0,<0.88.0`. Companion versions are
independent of official ty. Companion 0.87.0 was qualified against every ty release
from 0.0.84 through 0.0.99; its dependency range is `ty>=0.0.84,<0.1`. Future versions
within that range are accepted but need compatibility checks. An ordinary ty update
within a compatible group does not require another Django-ty release.

Django 5.0 through 6.1 and Python 3.10 or later are accepted. The
[compatibility matrix](docs/DJANGO-VERSIONS.md) records 21 complete Django/Python
pairs, each with 166 official-contract assertions, 83 independent runtime contracts
and nine QueryDict cases. Django 6.1.3 on Python 3.15 has an additional contract and
runtime qualification; the pinned mypy comparator does not declare support for that
Python version. See [the Monty guide](docs/MONTY.md) for the evidence and reproduction commands.

Versions through 0.5.0 depended on a checker distribution that owned the `ty`
namespace. Remove it before installing the new stack:

```sh
uv remove django-ty
uv add django-ty
uv run ty --version
uv run ty-extended --version
```

If you declared `ty-extended` separately, remove that old dependency too before
adding Django-ty again. For pip environments, uninstall `django-ty` and `ty-extended`
first, then install `django-ty` and reinstall official `ty`.

Change plugin-enabled commands and editor launchers from `ty` to `ty-extended`.
The `--runtime monty` option remains accepted; WASM selection is no longer supported.

## Coverage and qualification

The complete pinned Django static API is packaged in the wheel. No upstream
`django-stubs`, `django-stubs-ext` or mypy-plugin distribution is installed.
Django-ty covers model fields, relations, managers, queryset results, `values()`,
`values_list()`, basic `annotate()`, literal lookups and model ID state across
construction, loading, saving, deletion, aliases and branches. `WithAnnotations`
and other `django-stubs-ext` utilities remain outside the product surface.

Django documentation and the installed framework define expected behavior. Mypy
is a comparison tool; reviewed disagreements have version-specific references and
runtime evidence in the [disagreement audit](docs/MYPY-DISAGREEMENTS.md).
The [coverage map](docs/DJANGO-STUBS-COVERAGE.md) is generated from the same checks.

Installed-wheel CI tests automatic discovery, the module launcher, an empty `PATH`,
positive and negative typing controls, real LSP configuration, field hover, unsaved
errors, restoration and source preservation on Linux, macOS and Windows. A bounded
7,082-file/2,501-model regression checks both valid and invalid assignments. These
results qualify the recorded corpus and generated workload, not every private application.

## Development

```sh
python3 scripts/build-monty.py --check
bash scripts/build-wheel.sh
uv run --no-project --python 3.11 python scripts/evaluate_django_stubs_coverage.py --check
uv run --no-project --python 3.11 python -m unittest discover -s tests
bash scripts/differential-conformance.sh --check
uv run --no-project --python 3.11 python scripts/probe_django_versions.py --check --clean-environments
bash scripts/e2e.sh
```

The Rust crate is an independent development oracle. Its tests and 98% coverage gate
remain in CI; it is not part of the consumer build. Native test artifacts are cleaned
after each phase. The Python implementation also matches 151 native regression
responses through CPython and Monty 1.5.0. Consumers use the companion's embedded
runtime and do not depend on that separate development interpreter.

## License

MIT ([LICENSE](LICENSE)). Contributions are licensed under the same terms.
