# django-ty

`django-ty` adds Django ORM semantics to `ty-extended`. It installs Django,
the checker runtime, and a packaged Django static API for Django 5.0-6.1.

The tested compatibility matrix covering django-ty, ty-extended, Django, and
Python versions lives in
[docs/DJANGO-VERSIONS.md](https://github.com/regularkevvv/django-ty/blob/main/docs/DJANGO-VERSIONS.md).
Each Django line is probed against both the version-matched `mypy` +
`django-stubs` comparison and the shipped wheel.

## Install

```sh
uv add django-ty
```

Installed plugin discovery is deliberately opt-in. Add this to the project
configuration:

```toml
[tool.ty.plugins]
auto-discover = true
```

Then run:

```sh
uv run ty check .
```

No installer command, `.ty` directory, or file copy is needed.

## Coverage

The complete pinned static API is packaged inside the wheel. No upstream
`django-stubs`, `django-stubs-ext`, or mypy-plugin distribution is installed.
Utilities supplied by `django-stubs-ext`, including `WithAnnotations`, are
intentionally outside `django-ty`'s product surface. `django-ty` handles Django
model fields, forward and reverse relations, model-specific managers, queryset
result types, `values()`, `values_list()`, basic `annotate()`, and literal lookup
validation. Auto-primary-key state follows construction, loading, saving, and
deletion; aliases and branches are handled by ty-extended 0.84.4+.

Django's official documentation defines the expected behavior. All **166
assertions across 38 capabilities** pass on the **18 supported Django/Python
pairs** from Django 5.0 through 6.1. Independent runtime checks cover 83 reviewed
contracts and nine QueryDict assignment cases on each pair.

Mypy is a comparison tool. Its disagreements are listed with version-specific
Django references and runtime evidence in the
[compatibility matrix](https://github.com/regularkevvv/django-ty/blob/main/docs/DJANGO-VERSIONS.md).
The [disagreement audit](docs/MYPY-DISAGREEMENTS.md) explains upstream typing
policies, historical feature gaps, and the fixes made after that review.
CI rejects new unreviewed disagreements. The
[coverage map](https://github.com/regularkevvv/django-ty/blob/main/docs/DJANGO-STUBS-COVERAGE.md)
is generated from the same checks.

These results cover the tested corpus. They do not establish compatibility with
every Django API, custom AppConfig label, or dynamically registered model.

## Python alternative

This branch includes an experimental Python plugin for the embedded Monty
runtime. WASM remains the default. See [the analysis and checks](docs/MONTY-EXPERIMENT.md)
for selecting either backend from the same wheel and benchmarking them.

## Development

```sh
uv run --no-project --python 3.11 python scripts/evaluate_django_stubs_coverage.py --check
uv run --no-project --python 3.11 python -m unittest discover -s tests
bash scripts/differential-conformance.sh --check
uv run --no-project --python 3.11 python scripts/probe_django_versions.py --check
cargo test --locked
cargo llvm-cov --locked --all-targets --summary-only --fail-under-lines 98
bash scripts/e2e.sh
```

To refresh the vendored static API from the reviewed pinned checkout:

```sh
uv run --no-project --python 3.11 python scripts/vendor_django_static_api.py --upstream-root /path/to/django-stubs-6.1.1
bash scripts/differential-conformance.sh --write
uv run --no-project --python 3.11 python scripts/evaluate_django_stubs_coverage.py --write --check
```

## License

django-ty is licensed under the [MIT License](LICENSE). By submitting a contribution for inclusion
in django-ty, you agree that the contribution is licensed under the MIT License without additional
terms or conditions.
