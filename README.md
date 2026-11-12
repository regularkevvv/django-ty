# django-ty

`django-ty` adds Django ORM semantics through the **ty-extended Monty companion**.
The companion delegates to unchanged official Astral ty; it is not a fork of the checker.
Django's hooks and static API ship in one universal Python wheel. Consumers do not
build Rust, install WASM artifacts or run a Python worker.

## Native Ty experiment

This branch is testing a `django-types==0.24.0` declaration base so unchanged
native Ty handles ordinary Django fields, while Monty supplies Django-ty's
additional constructor, query, relation and model-state checks. The companion's
manifest selects an unreleased native projection strategy. No consumer
installation change is qualified yet.

The release ceiling is at most three times bare official Ty for every workload
median and every paired repeat across all five benchmark shapes. The latest
completed v58 trial passes the small and single-module stress shapes locally;
the distributed, many-files and distributed-stress shapes fail the strict
ceiling. Release remains blocked. Independent call handlers are batched after
an explicit statelessness promise; grouped initialization matches fresh handlers
across model scopes and primary-key shapes. The subsequent class-reference and
combined-record candidate has passed source-level checks; its optimized timing
is pending. See the
[companion performance results](https://github.com/regularkevvv/ty-extended/blob/perf/sparse-companion-analysis/docs/performance.md).

The following measurements describe earlier source checkpoints:

The v24 source passes 172 contract and row cases in memory mode, generic SDK
field checks and runtime-backed API controls in both projection modes, and eight
focused regressions on every official Ty release from 0.0.84 through 0.0.99,
using Python 3.13 and Django 6.1.3. It also passes 20 focused ORM cases, four
model-name ambiguity cases, and the larger Django example in both modes. The
example has zero positive-case diagnostics and all nine expected negative-case
diagnostics. All 19 broader companion SDK/editor suites pass in each mode.

Five alternating fresh-process samples of the 7,082-file, 2,501-model workload
measure **1.881 seconds** with the two-worker companion and **1.788 seconds**
with up to eight source-loading/copy workers. Both use identical Django code,
declarations and official Ty. Both pass all 100 assertions, both error controls
and 20 focused ORM cases. The largest candidate sample is **1.813 seconds**;
the one-second target remains unmet. `TY_MAX_PARALLELISM` bounds both the
companion workers and native Ty. Three samples per thread limit measure total
medians of 2.227, 1.935, 1.814 and 1.798 seconds at 1, 2, 4 and 8 threads.
See the [v24 qualification receipt](https://github.com/regularkevvv/ty-extended/blob/main/docs/qualification/native-django-parallel-v24.json)
for every observation, source identity and the source-only qualification scope.

The compact private Django index retains the full decoded model/hook contracts;
27,511 comparisons match the preceding representation, and a legacy opt-out
remains available. Payload size falls from 2,853,625 to 1,100,506 bytes. In a
separate same-binary comparison, that change reduced the median from 2.040 to
1.949 seconds. It does not remove the project-index pass.

The earlier [v20d four-stack comparison](https://github.com/regularkevvv/ty-extended/blob/main/docs/qualification/native-django-hybrid-v20d.json)
measured the hybrid at 2.076 seconds, MyPy at 7.136 seconds and official Ty with
django-types at 0.323 seconds. All pass 100 assertions and two error controls;
the focused ORM set matches 20/20 for the hybrid and 8/20 for native Ty. Those
measurements are a separate series from the v24 threading comparison.

The native declaration tree is reproducible with
`scripts/vendor_native_django.py`: it verifies the complete pinned django-types
0.24.0 and Django-ty 0.7.0 input trees, restores the recorded newer modules, and
applies eight explicit adapters. Its default mode checks all 731 packaged static
files without writing. See `compatibility/native-types-vendor.json` for input
hashes and the exact adapters. Reproduction does not prove API completeness.

The native base changes explicit annotation conventions: `CharField[Any, Any]`
becomes `CharField[Any]`, and `QuerySet[Model, Model]` becomes `QuerySet[Model]`.
Row-specific querysets use `ValuesQuerySet[Model, Row]`. See
`compatibility/native-types-migration.json`; no behavioral expectations were
removed from the conformance corpus.

Full static API, automatic consumer activation, installed-wheel/editor,
Django/Python matrix and hosted-CI checks remain release gates. Python tests are
68/69: the existing full-conformance receipt is stale and remains a failing gate.
The complete API and release qualification below describes the published 0.7.0
baseline; it does not establish compatibility of this new declaration base.

The current development profile keeps the complete model index while combining
plain-model traits and deferred fields in private index format 2. Readers retain
format 1 support. Reverse-manager annotations are expanded on access. On a
companion that offers bounded immutable class snapshots, an explicit
`companion-source-class-lookups` opt-in can retain class references instead of
sending their field summaries back through the plugin response. This experimental
option is disabled by default: a same-binary phase comparison showed that its
host preparation outweighed the guest savings. Other hosts and unsupported
snapshots retain the existing representation. These changes are under performance
qualification; they do not establish the required 3-times native Ty ceiling.
The complete comparison preserves 10,004 reconstructed class requests, 10,000
reverse-member responses and 800 ordinary call responses across four cases.
Python validation currently passes 68 of 69 tests; the stale official-contract
receipt remains an explicit release blocker.

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

## Performance

Django-ty 0.7 uses class-specific project indexes, bounded class batches and
read-only lookups in companion 0.89. Model relations within a split `models` package resolve across
sibling modules. See [the performance comparison](https://github.com/regularkevvv/ty-extended/blob/main/docs/performance.md)
for fresh-process MyPy and bare-ty benchmarks with ORM and ordinary Python error
controls, and [the Monty guide](docs/MONTY.md#large-project-performance) for the
installed large-project regression.

On the recorded macOS workload with 7,082 Python files, 2,501 related models and
100 ORM type assertions, the published 0.89 companion with the Django-ty 0.7
candidate wheel takes a median **6.59 seconds**, down from
**80.79 seconds** with Django-ty 0.6 and companion 0.87. MyPy with django-stubs takes
**6.81 seconds** on the same files; bare official ty takes
**0.27 seconds**. All five public-companion workloads meet the
MyPy median ceiling. The largest Mac case is close to parity; smaller projects
show larger advantages. These are five rotated fresh-process runs with exact ORM
assertions, both negative controls and unchanged source bytes. The
[qualification receipt](compatibility/companion-local-qualification.json) identifies
the executables and every sample; Django's published wheel is verified separately.

## Versions and migration

Django-ty 0.7.0 requires `ty-extended>=0.89.0,<0.90.0`. Companion versions are
independent of official ty. Companion 0.89.0 was qualified against every ty release
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
after each phase. The Python implementation also matches 156 native regression
responses through CPython and Monty 1.5.0. Consumers use the companion's embedded
runtime and do not depend on that separate development interpreter.

## License

MIT ([LICENSE](LICENSE)). Contributions are licensed under the same terms.
