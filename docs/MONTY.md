# Django on the Monty companion

Django-ty 0.6.0 ships the handwritten Python hooks in `python/django_ty/monty.py`
and the reviewed static Django API. Its canonical `ty-plugin.json` selects Monty;
`ty-plugin-monty.json` remains an identical compatibility alias. Source, manifests
and wheel metadata are checked together. The consumer wheel and source archive
build with Hatchling without a Rust or WASM toolchain.

The installed `ty-extended` binary executes the hooks in embedded Monty 1.5.0 and
delegates checking to unchanged official ty. The plugin receives project facts
through protocol 0.7; it does not import or execute a project's Django application.
Python SDK helpers come from `ty_extended.plugin_sdk`. `TYPE_CHECKING` declarations
in `_monty_sdk.pyi` and `_monty_types.pyi` describe the ambient SDK and wire data;
there is no separate interpreter or `pydantic-monty` consumer dependency.

## Compatibility evidence

The [version matrix](DJANGO-VERSIONS.md) records 21 complete Django/Python pairs
including Django 6.1.3. Each checks all 166 assertions over 38 capabilities,
83 framework runtime contracts and nine QueryDict cases. The native reference and
CPython/Monty response replay remain independent checks. Native reference line
coverage is 98.23%; the unchanged runtime/protocol corpus has 151 responses per interpreter.

Python 3.15 has a separate Django 6.1.3 qualification using the same official
assertions and actual framework runtime. Its mypy baseline runs on Python 3.13:
that pinned django-stubs release does not declare Python 3.15 support. The full
version-matched matrix is therefore reported separately from this qualification.

The companion's [qualified ty group](https://github.com/regularkevvv/ty-extended/blob/main/docs/compatibility.md)
spans 0.0.84 through 0.0.99. Package dependencies constrain companion versions,
not one upstream ty patch. Later ty releases are accepted within its dependency
range and checked by compatibility CI.

## Installed CLI and editor checks

CI builds one universal wheel, then installs that exact artifact on Linux, macOS
and Windows. It checks discovery, default module invocation, empty-PATH resolution,
negative diagnostics, real LSP configuration requests, field hover, unsaved errors,
restoration and original source bytes.

Django editor sessions require `diagnosticMode = "workspace"`. Project-index
requests otherwise contain only checked/open files; closed model definitions are
needed for reverse relations and queryset annotations. A controlled comparison
reproduces the limitation with the former checker and passes in workspace mode
with both backends. See the [editor settings](../README.md#editors).

Reproduce installed qualification:

```sh
uv run --no-project --python 3.13 --with /path/to/django_ty-0.6.0-py3-none-any.whl python scripts/check_companion_install.py --output /tmp/new-django-editor-receipt
```

## Large-project regression

```sh
uv run --no-project --python 3.13 --with /path/to/django_ty-0.6.0-py3-none-any.whl --with Django==6.1.3 python scripts/check_companion_scalability.py --output /tmp/new-django-scale-receipt
```

The default workload contains 7,082 Python files and 2,501 related models. Positive
and negative controls must finish in 180 seconds and below 3,072 MiB sampled
combined checker-process RSS. A limit failure terminates only the test's own
process group. Original source bytes must remain unchanged. Temporary projections
and task-owned caches are removed after each run. These are workload acceptance
bounds, not a universal application memory limit.

## Historical experiments

Earlier dual-runtime benchmarks and design notes are preserved under
[history/0.5](history/0.5/MONTY-EXPERIMENT.md). They describe unreleased experiments
and older checker distributions; their timings do not describe the current companion.
