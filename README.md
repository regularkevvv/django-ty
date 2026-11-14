# django-ty

Django ORM support for [ty-extended](https://github.com/regularkevvv/ty-extended).
Official Ty checks ordinary Python and Django fields; django-ty adds constructor, relation, query result and model-state checks. Plugins use the Python subset supported by Monty. The package ships one universal Python wheel and runs without building Rust or starting a Python plugin worker.

## Install and check

```sh
uv add django-ty
```

Enable installed plugin discovery:

```toml
[tool.ty.plugins]
auto-discover = true
```

```sh
uv run ty-extended check .
```

Select a settings module when it cannot be inferred:

```sh
uv run python -m django_ty --settings-module project.settings check .
```

The module launcher finds the installed executable even when it is absent from `PATH`.

## Editors

Start `ty-extended server` and enable workspace diagnostics so closed model modules contribute reverse relations and cross-module queryset information.

For the official VS Code extension, use a trusted workspace:

```json
{
  "ty.path": ["/absolute/project/.venv/bin/ty-extended"],
  "ty.diagnosticMode": "workspace"
}
```

On Windows, use `.venv/Scripts/ty-extended.exe`. For Neovim 0.11 or later:

```lua
vim.lsp.config("ty", {
  cmd = { "/absolute/project/.venv/bin/ty-extended", "server" },
  settings = { ty = { diagnosticMode = "workspace" } },
})
vim.lsp.enable("ty")
```

## Django behavior

The plugin checks model constructors, raw relation keys, custom primary keys, inherited fields, reverse relations, managers, query results, literal lookups and creation defaults. It infers `values()` dictionaries and `values_list()` rows, including lazy `.get()` results and no-argument field order. Model ID state follows construction, loading, saving, deletion, aliases and branches.

Native ORM declarations come from django-types 0.24.0. Reviewed modern Django declarations and adapters preserve newer APIs, including widgets, async pagination, validators and email attachments. The complete packaged declaration tree is reproducible from pinned inputs; hashes, module overlays and adapters are recorded in [the provider receipt](compatibility/native-types-vendor.json).

The package does not install django-stubs, django-stubs-ext or MyPy. `WithAnnotations` and other django-stubs-ext utilities remain outside the supported surface. Native field and queryset annotations use conventions such as `CharField[str]` and `QuerySet[Book]`; row-specific querysets use `ValuesQuerySet[Model, Row]`. See [the migration inventory](compatibility/native-types-migration.json).

## Versions

Django-ty 0.8 requires `ty-extended>=0.90.0,<1.0`, Django `>=5.0,<6.2` and Python `>=3.10`. The native integration requires `ty>=0.0.101,<0.1` and is qualified on every release from 0.0.101 through 0.0.104. ty-extended releases are independent of official Ty; ordinary Ty updates within a compatible group do not require a Django-ty release.

The [Django/Python matrix](docs/DJANGO-VERSIONS.md) records tested combinations and the versions of each comparator. [Ty compatibility](https://github.com/regularkevvv/ty-extended/blob/main/docs/compatibility.md) records the independently qualified checker groups. Future upstream releases need compatibility checks before being described as tested.

Versions through django-ty 0.5 used a distribution that owned the `ty` command. Remove old django-ty and ty-extended packages before installing the current stack, reinstall official `ty`, and change plugin-enabled commands and editor launchers to `ty-extended`.

## Performance and correctness

Native field inference avoids generating replacement declarations for every ordinary Django field. Scoped indexes, bounded batches, shared type factories and lazy row construction reduce the remaining plugin work. [Benchmarks](https://github.com/regularkevvv/ty-extended/blob/main/docs/performance.md) compare identical generated projects against native official Ty with django-types and MyPy with its Django plugin, retaining all samples and negative controls.

Django's documentation defines expected behavior. The installed framework independently checks reviewed disagreements; MyPy is a comparator. The [coverage map](docs/DJANGO-STUBS-COVERAGE.md) records 172 line-level contracts and their exact evidence. The separate modern API regression includes eight positive assertions and three intentional errors, plus runtime controls. These are measured contracts, not a claim about every Django API or application.

Installed-wheel checks cover discovery, the module launcher, an empty `PATH`, real editor sessions, hover, unsaved errors, restoration and source preservation. [Runtime and qualification instructions](docs/MONTY.md) describe reproduction and the release gates.

## Development

```sh
python scripts/build-monty.py --check
bash scripts/build-wheel.sh
python scripts/audit_stub_imports.py
python scripts/evaluate_django_stubs_coverage.py --check
python -m unittest discover -s tests
bash scripts/differential-conformance.sh --check
python scripts/probe_django_versions.py --check --clean-environments
```

The Python environment running SDK tests needs ty-extended installed. The historical Rust reference supplies regression requests. Current interpreter parity compares complete CPython and Monty responses; Django runtime contracts provide the independent semantic checks. Consumers use the packaged Python plugin in embedded Monty.

MIT. [Third-party notices](THIRD_PARTY_NOTICES.md) cover the declaration providers.
