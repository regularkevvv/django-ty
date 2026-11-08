# Django on the Monty companion

Django-ty 0.7.0 ships the handwritten Python hooks in `python/django_ty/monty.py`
and the reviewed static Django API. Its canonical `ty-plugin.json` selects Monty;
`ty-plugin-monty.json` remains an identical compatibility alias. Source, manifests
and wheel metadata are checked together. The consumer wheel and source archive
build with Hatchling without a Rust or WASM toolchain.

The installed `ty-extended` binary executes the hooks in embedded Monty 1.5.0 and
delegates checking to unchanged official ty. The plugin receives project facts
through protocol 0.9; it does not import or execute a project's Django application.
Python SDK helpers come from `ty_extended.plugin_sdk`. `TYPE_CHECKING` declarations
in `_monty_sdk.pyi` and `_monty_types.pyi` describe the ambient SDK and wire data;
there is no separate interpreter or `pydantic-monty` consumer dependency.

## Compatibility evidence

The [version matrix](DJANGO-VERSIONS.md) records 21 complete Django/Python pairs
including Django 6.1.3. Each checks all 166 assertions over 38 capabilities,
83 framework runtime contracts and nine QueryDict cases. The native reference retains SDK 0.0.8 as an independent semantic baseline.
CPython/Monty replay compares those original protocol fields and separately checks
the exact packaged manifest. The development candidate additionally compares
2,585 scoped class results and 3,017 ordered batches with full-index CPython
results through standalone Monty. Native reference line
coverage is enforced at 98%; the runtime/protocol corpus includes cross-module
model relations and has 156 responses per interpreter in the current development tree.

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
uv venv --python 3.13 /tmp/django-qualification
uv pip install --python /tmp/django-qualification/bin/python /path/to/django_ty-0.7.0-py3-none-any.whl Django==6.1.3
/tmp/django-qualification/bin/python scripts/check_companion_install.py --output /tmp/new-django-editor-receipt
```

Use an explicit installed environment: `uv run --with` can layer dependencies
outside `sys.executable`'s environment, which these subprocess checks pass to ty.
On Windows, use the environment's `Scripts/python.exe` in place of `bin/python`.

## Large-project performance

The development candidate uses fully qualified `Manager[Model]` annotations for
ordinary managers. It retains generated manager classes for custom QuerySet
methods and keeps the virtual row types used by `values()` and `values_list()`.
Unused per-model QuerySet declarations are removed. Class hooks read their scoped
index without copying it; regressions check that hooks preserve shared input.
This candidate needs the companion's imported-class qualification fix before a
Django release can declare compatibility with that companion version.
Its [local qualification receipt](../compatibility/manager-projection-candidate.json)
records the installed-wheel checks across all 21 Django/Python pairs, exact
published-companion diagnostics, native replay and coverage. Hosted CI and
published-artifact acceptance remain separate gates.

A [later companion qualification](https://github.com/regularkevvv/ty-extended/blob/f75e7d4a170aa976a6d24d8a46e8c480b3aa077d/docs/qualification/field-access-projection.json)
uses these unchanged Django sources with the corrected field projection. All 166
assertions and six error controls pass on each of the 16 supported Ty versions
with Django 6.1.3. The full stress fixture measures 5.187 seconds versus MyPy's
6.560 seconds in that paired series; the one-second target remains unmet. The
21-pair installed matrix above retains its earlier companion identity.

Django-ty 0.7 supplies a reduced index for each class and looks up additional
model data through the companion's read-only index interface. It opts into bounded
class batches, preserving the response order and individual class results. The
companion limits each batch to 128 classes and 1 MiB of request data; oversized
classes and failed batches use the ordinary individual hook. Unqualified
relations between sibling modules in an app's `models` package resolve to the
same model as Django; an unrelated app's model is not a fallback.

The companion [benchmark harness](https://github.com/regularkevvv/ty-extended/blob/main/docs/performance.md)
compares fresh public CLI processes against MyPy plus django-stubs and bare
official ty. It checks exact ORM types and rejects intentional Django and
ordinary Python errors before accepting timings.

The installed resource-bound regression is also retained:

```sh
/tmp/django-qualification/bin/python scripts/check_companion_scalability.py --output /tmp/new-django-scale-receipt
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
