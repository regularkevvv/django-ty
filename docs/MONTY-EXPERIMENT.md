# Python/Monty alternative

The Python port implements the Rust plugin's rules on ty-extended 0.84.4. **One
wheel contains both implementations and the shared stub tree.** WASM remains the
usual auto-discovery default; Monty is an explicit configuration choice. This
branch is an experiment, not a published release.

## Hooks

| Behavior | Hook | Rust reference |
| --- | --- | --- |
| Models, inheritance, managers, relations, settings, choices, virtual rows | `build-project-index` | [index.rs](../src/index.rs) |
| Fields and constructors | `analyze-class` | [fields.rs](../src/fields.rs), [plugin.rs](../src/plugin.rs) |
| Querysets, lookups, projections, prefetching, metadata, auth, app registry | `adjust-call-return` | [querysets.rs](../src/querysets.rs), [apps.rs](../src/apps.rs) |
| `Manager.from_queryset` | `adjust-call-signature` | [plugin.rs](../src/plugin.rs) |
| Constructor/load/save/delete ID facts | `adjust-call-state` | [state.rs](../src/state.rs) |
| Immutable QueryDict writes | `validate-mutation` | [diagnostics.rs](../src/diagnostics.rs) |

Alias tracking, branch joins and invalidation remain checker responsibilities.
Both plugins retain conservative rules for overrides, signals, uncertain saves,
custom loading, non-auto IDs and multi-table inheritance.

## Select a backend

Build and install once:

```sh
DIST_DIR=/tmp/django-ty-dist bash scripts/build-wheel.sh
uv add /tmp/django-ty-dist/django_ty-0.5.0-py3-none-any.whl
uv run python -m django_ty --runtime wasm check .
uv run python -m django_ty --runtime monty check .
```

The wrapper selects one plugin through ty's existing configuration options. If
your project configures `django-settings-module`, pass it to the explicit entry:

```sh
uv run python -m django_ty --runtime monty --settings-module project.settings check .
```

For a persistent configuration, print the entry and add it to `ty.toml`:

```sh
uv run python -m django_ty --runtime monty --settings-module project.settings --print-config
```

Printed artifact paths refer to the current environment; regenerate them after
moving it. Use the printed plugin entry's `config` for Django settings: the
`plugins.config.django-ty` table applies to auto-discovered packages. The wrapper
replaces the explicit plugin list and disables auto-discovery; include other
plugins manually if your project uses them. Other ty settings remain in effect.

No wheel replacement, manifest rewriting or `pydantic-monty` installation is
needed. The optional worker mode still uses `ty-extended[monty-workers]`.

## Python constraints

[monty.py](../python/django_ty/monty.py) uses the checker's
[public SDK](https://github.com/regularkevvv/ty-extended/blob/1e7e01dc34da874f494db30a49323e570ef8974a/python/ty/plugin_sdk.py).
It consumes host summaries; it cannot import Django, inspect live models, read
files or access the network. The host prepends the SDK to this single file.
Imports are guarded by `typing.TYPE_CHECKING`; runtime rules use functions and
plain dictionaries. The port avoids inheritance, `match`, generators and
third-party imports. Wildcard imports are rejected even inside a type-checking
block. See [authoring constraints](https://github.com/regularkevvv/ty-extended/blob/1e7e01dc34da874f494db30a49323e570ef8974a/docs/plugin-authoring.md#python-sandbox-constraints)
and [Monty documentation](https://pydantic.dev/docs/monty/).

All helpers and hooks have parameter and return annotations. Static-only
[`TypedDict` schemas](../python/django_ty/_monty_types.pyi) describe requests,
responses and model indexes; [SDK declarations](../python/django_ty/_monty_sdk.pyi)
refine the SDK's broad JSON aliases. Monty skips their `TYPE_CHECKING` imports.
Annotations do not validate runtime payloads.

CI runs ty on the implementation and schemas, verifies all 39 SDK signatures,
and checks that seven invalid payloads, SDK arguments, index writes and return
types are rejected. Repeat it with:

```sh
uv run --no-project --python 3.13 --with ty-extended==0.84.4 python scripts/check_monty_types.py
```

## Compatibility evidence

- 151 full protocol responses match Rust after SDK deserialization, in both
  CPython and pinned Monty 1.0.0. `pydantic-monty` is used only for this test.
- Both backends from the **same wheel** pass all 18 Django/Python pairs: 166/166
  assertions, 83 independent Django runtime contracts and nine QueryDict cases
  per pair. The baseline retains 100% official-contract coverage and 93.8%
  mypy agreement.
- Both pass positive, expected-negative and static API installed-wheel E2E.
  E2E also verifies that default auto-discovery still loads WASM and that both
  artifacts are installed without a Python Monty runtime dependency.
- Existing Rust tests and coverage remain CI gates; 32 Python tooling tests
  include backend configuration, path escaping and explicit settings forwarding.

This proves parity for the corpus, not all possible Django programs.

Both host runtimes cap responses at 8 MiB. The standalone 2,501-model Rust test
exceeds that cap; its protocol parity is not evidence of host support at that
size. Monty uses a five-second feed budget and recursion limit of 1,000 by
default, with no memory cap. Embedded Monty handles Python errors, execution
limits and unwinding panics, but cannot isolate native allocator/stack aborts.
WASM limits guest memory to 64 MiB and traps guest stack overflows. Worker mode
adds process isolation. See [host limits](https://github.com/regularkevvv/ruff-extended/blob/4da08f0a01d9f2611c20b77be8db84a919eceae3/crates/ty_plugin_host/src/monty.rs)
and [runtime safety](https://github.com/regularkevvv/ty-extended/blob/1e7e01dc34da874f494db30a49323e570ef8974a/docs/plugin-runtime.md#safety-model).

## Benchmark and stress test

[benchmark_runtimes.py](../scripts/benchmark_runtimes.py) selects both backends in
one installed E2E environment. It alternates backend order and launches fresh
checker processes, including startup and plugin initialization. Generated models
exercise fields, relations, queries and constructor/save/delete ID assertions.
It records wall time, CPU time, each checker's peak RSS, exit status and output.
Peak RSS includes the whole checker; it is not incremental plugin memory.

```sh
export DJANGO_TY_WHEEL=/tmp/django-ty-dist/django_ty-0.5.0-py3-none-any.whl
export DJANGO_TY_E2E_DIR=/tmp/django-ty-benchmark-e2e
bash scripts/e2e.sh
uv run --no-project --python 3.11 python scripts/benchmark_runtimes.py \
  --project "$DJANGO_TY_E2E_DIR" --runs 7 --models 0 5 25 --output /tmp/benchmark.json
# Explore limits; failures stay in the report. No speed ratio is produced for failing workloads.
uv run --no-project --python 3.11 python scripts/benchmark_runtimes.py \
  --project "$DJANGO_TY_E2E_DIR" --runs 1 --models 25 100 300 --relations chain \
  --timeout 30 --allow-failures --output /tmp/stress.json
```

CI runs a small benchmark and uploads raw JSON. It requires successful checks
but has no timing threshold: shared runners are unsuitable for speed regression
gates. Local measurements are in [the benchmark report](../compatibility/monty-experiment-benchmark.json).
OS cache state and machine load affect results. This measures fresh CLI checks,
not editor/watch-mode updates or isolated hook execution. To fix checker
parallelism for a comparison, prefix the command with `TY_MAX_PARALLELISM=1`.

On macOS arm64, Python 3.14.2 / Django 6.1.2 / ty-extended 0.84.4, seven runs
per backend with default checker parallelism gave these medians:

| Extra models | WASM time | Monty time | WASM peak RSS | Monty peak RSS |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 1.85 s | 2.34 s | 252 MiB | 629 MiB |
| 5 | 1.98 s | 2.76 s | 308 MiB | 768 MiB |
| 25 | 5.77 s | 2.14 s | 1,222 MiB | 446 MiB |

All 42 checks succeeded. Results are mixed: WASM was faster on the two smaller
cases, Monty on the larger one. Both showed wide variation between runs; the
raw samples matter more than a single speed claim.

The [relation-chain stress report](../compatibility/monty-experiment-stress.json)
records one attempt per backend at 25, 100 and 300 extra models. Both passed at
25 and 100. Both reached the benchmark's 30-second deadline at 300; peak checker
RSS was 3.34 GiB for WASM and 6.19 GiB for Monty. These are benchmark timeouts,
not evidence of plugin crashes or universal model-count limits.

### Compiled WASM cache

The cache implementation in [ruff-extended PR #41](https://github.com/regularkevvv/ruff-extended/pull/41)
and [ty-extended PR #37](https://github.com/regularkevvv/ty-extended/pull/37) compiles
WASM once into the trusted user cache. Subsequent checker launches load native
code directly. Plugin wheels still contain portable `.wasm` files.

The [controlled report](../compatibility/monty-cwasm-benchmark-single-thread.json)
compares fresh processes with an empty WASM cache, a primed compiled cache and
embedded Monty. Each size has seven runs per mode in rotating order. Host counters
confirm compilation misses for cold runs and hits without misses for cached runs.
The priming check is excluded from the medians.

On macOS arm64, with `TY_MAX_PARALLELISM=1`:

| Extra models | Cold WASM | Cached WASM | Monty |
| ---: | ---: | ---: | ---: |
| 0 | 2.08 s | 0.85 s | 0.87 s |
| 5 | 2.24 s | 1.01 s | 1.06 s |
| 25 | 3.17 s | 1.95 s | 2.04 s |

All 63 checks passed. Caching saves about 1.2 seconds here. Cached WASM has
roughly 3–4% lower medians than Monty; their full-check times are close.

The [default-parallelism report](../compatibility/monty-cwasm-benchmark-default.json)
also passes all 63 checks, but timings vary substantially. Cached WASM/Monty
medians are 0.96/2.22 s, 1.14/1.17 s and 4.86/2.36 s for 0/5/25 extra models.
The larger case favors Monty. These results do not establish a universal winner
or isolate individual hook execution.

Both reports use the same installed wheel and optimized checker built from the
reviewed cache source with release LTO disabled. Checker/source hashes and build
settings are recorded. These are experimental builds, not measurements of a
published cache-enabled release. Repeat with a cache-enabled checker:

```sh
TY_MAX_PARALLELISM=1 uv run --no-project --python 3.11 python scripts/benchmark_runtimes.py \
  --project "$DJANGO_TY_E2E_DIR" --ty-bin /path/to/cache-enabled/ty \
  --wasm-cache --runs 7 --models 0 5 25 --output /tmp/cwasm-benchmark.json
```

The published 0.84.4 checker cannot run the `--wasm-cache` comparison; missing
cache-hit evidence makes the benchmark fail instead of reporting a cached result.

## Repeat compatibility checks on one wheel

```sh
export DJANGO_TY_WHEEL=/tmp/django-ty-dist/django_ty-0.5.0-py3-none-any.whl
bash scripts/check-monty-parity.sh
for runtime in wasm monty; do
  export DJANGO_TY_RUNTIME="$runtime"
  bash scripts/differential-conformance.sh --check
  uv run --no-project --python 3.11 python scripts/probe_django_versions.py --check --reuse
  bash scripts/e2e.sh
done
```
