# Python/Monty alternative

**A complete Python alternative is possible with ty-extended 0.84.4.** No checker
changes are required. `python/django_ty/monty.py` implements the same rules as the
Rust plugin; the existing WASM implementation remains the default.

## What was ported

| Django behavior | Monty hook | Rust reference |
| --- | --- | --- |
| Models, inheritance, managers, reverse relations, settings, choices, virtual rows | `build-project-index` | [`index.rs`](../src/index.rs) |
| Field descriptors and constructors | `analyze-class` | [`fields.rs`](../src/fields.rs), [`plugin.rs`](../src/plugin.rs) |
| Querysets, lookups, projections, annotations, prefetching, metadata, lazy strings, auth and app registry | `adjust-call-return` | [`querysets.rs`](../src/querysets.rs), [`apps.rs`](../src/apps.rs) |
| `Manager.from_queryset` | `adjust-call-signature` | [`plugin.rs`](../src/plugin.rs) |
| Constructor/load/save/delete ID facts | `adjust-call-state` | [`state.rs`](../src/state.rs) |
| Immutable QueryDict writes | `validate-mutation` | [`diagnostics.rs`](../src/diagnostics.rs) |

Both runtimes receive the same protocol data and use the same stub tree. Alias
tracking, branch joins and invalidation still belong to the checker. Python
retains the conservative rules for overridden methods, uncertain saves, signal
receivers, custom loading, non-auto IDs and multi-table inheritance.

The [Python SDK](https://github.com/regularkevvv/ty-extended/blob/1e7e01dc34da874f494db30a49323e570ef8974a/python/ty/plugin_sdk.py)
exposes these hooks and their complete response shapes, including structural type
snapshots, cross-symbol contributions and constructor state claims. The port
uses those public builders; it does not call the Rust Django plugin.

## Python means the Monty subset

This is sandboxed Python, not a normal CPython Django plugin. It cannot import
Django, read project files, inspect live model classes or access the network.
The host supplies class summaries, literal arguments, settings and the project
index. That is sufficient because the Rust implementation already works from
those summaries.

The host prepends the SDK to a single source file. Imports from `ty.plugin_sdk`
are guarded by `typing.TYPE_CHECKING` for editors. The port uses functions and
plain dictionaries rather than Rust structs/enums. It avoids inheritance,
`match`, generators and third-party imports. Wildcard imports are rejected by
the pinned interpreter, even inside an unexecuted type-checking block.
See the checker's [authoring constraints](https://github.com/regularkevvv/ty-extended/blob/1e7e01dc34da874f494db30a49323e570ef8974a/docs/plugin-authoring.md#python-sandbox-constraints)
and [Monty documentation](https://pydantic.dev/docs/monty/).

The default embedded runtime requires **no `pydantic-monty` installation**. The
parity tests install version 1.0.0 only to run an independent Monty worker with
the same interpreter version. That is a development dependency. Explicit ty
worker mode requires the existing `ty-extended[monty-workers]` extra.

## Try it

Build the alternative without a Rust compiler or WASM artifact:

```sh
DJANGO_TY_RUNTIME=monty DIST_DIR=/tmp/django-ty-monty-dist bash scripts/build-wheel.sh
uv add /tmp/django-ty-monty-dist/django_ty-0.5.0-py3-none-any.whl
```

Use the usual configuration:

```toml
[tool.ty.plugins]
auto-discover = true
```

The alternative wheel registers Monty through its canonical `ty-plugin.json`.
It replaces the WASM wheel in that environment; it does not register a second
plugin with competing claims. It is an experiment on this branch, not a new
published version.

The normal wheel also contains the Python artifact and `ty-plugin-monty.json`
for explicit configuration. If selecting it manually, disable auto-discovery
and set `plugins.enabled = true`, `path`, `manifest-path`, `runtime = "monty"`,
`trusted = true`, and
`stub-overlay-path` to the installed package's `stubs` directory.

## Evidence and limits

- All 50 existing Rust tests and 26 Python tooling tests pass; Rust line coverage
  remains 98.23%.
- The regression recorder captures 150 hook requests. CPython and Monty replay
  them plus the packaged manifest. All **151 responses** equal Rust after SDK
  deserialization, including defaults, diagnostics, imports and nested snapshots.
- The Python-only installed wheel passes all **18 Django/Python pairs**, each
  with **166/166 assertions**, 83 independent Django runtime contracts and nine
  QueryDict cases. The baseline retains 100% official-contract coverage and
  93.8% mypy agreement.
- Installed-wheel E2E checks cover positive, expected-negative and static API
  fixtures. The WASM default passes the same E2E checks. Disabled-plugin/state
  controls reject the expected assertions; explicit selection from the default
  wheel succeeds. The Python source archive rebuilds an identical package payload.

These results establish parity for the existing corpus, not every possible
Django program. Independent runtime proofs still check Django itself; they do
not treat either plugin as the specification.

Both checker runtimes reject responses over **8 MiB**. The 2,501-model native
stress test generates a response larger than that: it passes standalone
protocol parity but is not proof that either checker runtime can load that
project unchanged. Monty replay uses ty's default five-second feed budget and
recursion limit of 1,000. No memory cap is set by default.

Embedded Monty handles Python errors, execution limits and unwinding panics,
but cannot isolate native allocator/stack aborts or enforce an allocator memory
cap. WASM has a 64 MiB guest-memory limit and traps guest stack overflows.
Worker mode offers process isolation at an additional deployment cost. See the
[actual host limits](https://github.com/regularkevvv/ruff-extended/blob/4da08f0a01d9f2611c20b77be8db84a919eceae3/crates/ty_plugin_host/src/monty.rs)
and the checker's [runtime safety model](https://github.com/regularkevvv/ty-extended/blob/1e7e01dc34da874f494db30a49323e570ef8974a/docs/plugin-runtime.md#safety-model).

## Size and timing

Measured locally on macOS arm64 with Python 3.14.2, Django 6.1.2 and ty-extended
0.84.4, using identical fixture sources and seven alternating fresh checker
processes. [Raw measurements](../compatibility/monty-experiment-benchmark.json)
and [`benchmark_runtimes.py`](../scripts/benchmark_runtimes.py) preserve the method.

| Measurement | WASM default on this branch | Python-only alternative |
| --- | ---: | ---: |
| Plugin wheel | 796,615 bytes | 496,910 bytes |
| Positive + static API fixture, median | 3.39 s | 0.93 s |
| Observed timing range | 1.86–3.48 s | 0.83–2.68 s |

The Python source is 87,249 bytes, compressed to 14,680 bytes in the alternative
wheel. The packaged stub tree is shared. The checker/runtime package does not
change. Timings vary by over a second between runs; this one fixture does not
establish general throughput or memory use.

The practical tradeoff is easier rule maintenance and a compiler-free plugin
build, while retaining the checker's Rust/Monty runtime and its sandbox limits.
Two implementations also create maintenance work: CI must require response
parity and run both installed wheels. This branch adds those gates.

## Repeat the checks

```sh
bash scripts/check-monty-parity.sh
DJANGO_TY_RUNTIME=monty bash scripts/differential-conformance.sh --check
DJANGO_TY_RUNTIME=monty uv run --no-project --python 3.11 python scripts/probe_django_versions.py --check --reuse
DJANGO_TY_RUNTIME=monty bash scripts/e2e.sh
```
