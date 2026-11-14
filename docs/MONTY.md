# Django plugin runtime

Django-ty 0.8 ships its Python hooks, native ORM declarations and reviewed modern static API in one universal wheel. `ty-plugin.json` selects embedded Monty; `ty-plugin-monty.json` remains an equivalent registration alias. ty-extended executes the hooks in its embedded runtime and delegates checking to unchanged official Ty.

## Installation and configuration

Install django-ty and enable automatic plugin discovery as shown in [the README](../README.md). The package requires ty-extended 0.90 or later within the declared dependency range. No Python plugin interpreter, WASM artifact or Rust build is required for consumers.

For an explicit settings module:

```sh
python -m django_ty --settings-module project.settings check .
```

The launcher resolves the installed ty-extended executable directly. Configure editors to launch `ty-extended server` with workspace diagnostics so closed model modules remain available to the Django index.

## Declaration providers

The native ORM layer uses django-types 0.24.0 field and queryset generics. Modern static declarations are retained from the reviewed django-ty 0.7 tree, based on django-stubs 6.1.1. Explicit adapters bridge callback and generic shapes. The MyPy comparison uses a separate environment and does not become a candidate dependency.

The provider receipt records hashes for both complete inputs, every module overlay, every adapter preimage and the final tree. Reproduce or check it with:

```sh
python scripts/vendor_native_django.py \
  --django-types-root /path/to/django-types-0.24.0/django-stubs \
  --legacy-root /path/to/django-ty-0.7.0/django_ty/stubs/django
python scripts/audit_stub_imports.py
```

The default provider command verifies without writing. `--write` regenerates only after both pinned input trees and every adapter have passed verification. The import audit catches unresolved Django-local dependencies across module reexports. Neither an inventory nor a tree hash alone establishes semantic completeness.

## Qualification

Django's documentation and installed runtime define the contracts. [The generated coverage map](DJANGO-STUBS-COVERAGE.md) separates those results from MyPy agreement and static declaration inventory. [The version matrix](DJANGO-VERSIONS.md) records each supported Django/Python combination. Current and historical receipts retain their original executable identities.

Use separate installed environments for candidate and MyPy checks. For the candidate:

```sh
uv venv --python 3.13 /tmp/django-qualification
uv pip install --python /tmp/django-qualification/bin/python dist/django_ty-*.whl
/tmp/django-qualification/bin/python scripts/check_companion_install.py --output /tmp/new-django-editor-receipt
/tmp/django-qualification/bin/python scripts/check_modern_static_api.py --output /tmp/new-modern-api-receipt
```

The modern API check requires Django 6.1 or later. It verifies widgets, validators, email attachments and async pagination through both type checking and the installed runtime. Installed editor tests cover automatic discovery, entry points, empty PATH, positive and negative typing controls, hover, unsaved changes and restoration.

## Large-project performance

Ordinary fields remain native. The plugin uses scoped immutable indexes, bounded class batches, shared result factories and lazy row construction. Internal index format 2 retains format 1 reading support. Model relations in a split models package resolve across sibling modules; unrelated applications are not fallback matches.

The [benchmark report](https://github.com/regularkevvv/ty-extended/blob/main/docs/performance.md) compares fresh public CLI processes against native Ty with django-types and MyPy with django-stubs. It preserves ordinary Python and ORM error controls as well as every timing sample. The accepted policy checks both mean and median ratios; it does not promise a worst-case bound for arbitrary projects.

The installed resource regression is retained:

```sh
/tmp/django-qualification/bin/python scripts/check_companion_scalability.py --output /tmp/new-django-scale-receipt
```

It checks 7,082 files and 2,501 models with source preservation, valid and invalid assignments, timeout and process-tree memory limits. Task-owned projections and caches are removed after checks.

## Development references

The Python hooks are the shipped implementation. The historical native Rust library supplies regression requests and retains its own tests. Its eager index and django-stubs types are not expected output for the new native declaration strategy. Development parity checks compare complete CPython and Monty responses, including opaque indexes and new protocol fields; Django runtime contracts supply the independent semantic reference. No native library is loaded by the product. Historical WASM and external-worker instructions belong to [older releases](history/0.5/MONTY-EXPERIMENT.md).
