# Django Compatibility Map

Static declaration baseline: [`django-stubs` 6.1.1](https://github.com/typeddjango/django-stubs/tree/c7816bcf4cb8ec8706acb5b671ca62131b345ef7) at `c7816bcf4cb8ec8706acb5b671ca62131b345ef7`.

`django-ty` vendors the pinned declaration tree inside its wheel. It neither installs nor executes the upstream mypy plugin.

Reviewed adaptations inline TemplatesSetting and add a mutable request helper used only by the exact HttpRequest constructor hook. Custom subclasses retain their identity; framework request types stay immutable. Typing imports use typing_extensions, and enum declarations have Python 3.10 fallbacks. The same transformations are applied during upstream fingerprint verification, and scripts/check_querydict_runtime.py compares nine assignment cases with the installed Django runtime.

## Measured Surface

- Vendored static declaration inventory: 712 `.pyi` modules and 16879 public symbols are packaged in the wheel.
- Vendored static-tree SHA-256: `fc4a572a925776c7b2e45364dd22c44a91089c0ed82ad291ca8c45a228f3523f`.
- Documented feature contract coverage: **100.0%** across 38 reviewed capabilities (38 supported, 0 partial, 0 unsupported).
- Assertion conformance: **100.0%** (119 of 119 documented expectations matched).
- Candidate host: `django-ty` 0.5.0 on `ty-extended` 0.84.2 at `0c1c84c1340ab818faa328a32a48048ebf06d105`.
- Target: **95%** documented contract coverage. The static score is deliberately separate and does not hide semantic gaps.

Auxiliary `django-stubs-ext` utilities such as `WithAnnotations` are outside this Django-behavior inventory. The candidate wheel must not install or package `django-stubs`, `django-stubs-ext`, or mypy; generic `Annotated` transport remains a library-neutral ty-extended plugin capability.

Literal apps.get_model lookups currently resolve conventional app labels. Custom AppConfig labels and dynamically computed registry names are outside the measured surface.

## Methodology

The inventory maps every transformer module in the pinned django-stubs plugin to reviewed capabilities with version-specific official Django documentation references. Each capability has at least two line-level assertions in one shared Django project.

Django's official documentation defines each assertion's expected behavior. The installed Django runtime independently checks reviewed differences, and ty checks the corresponding static assertions. Mypy plus django-stubs is a comparator. A new unexplained disagreement or missing runtime proof invalidates the run; agreeing with mypy cannot override documented Django behavior.

Feature-balanced contract coverage gives every capability equal weight. Assertion conformance reports the raw candidate matches. Mypy agreement is retained separately as comparison evidence. These scores cover this corpus and its documented assumptions, not every Django API or project configuration.

## Dynamic Coverage

| Area | Capabilities | Contract coverage |
| --- | ---: | ---: |
| Django extras | 6 | 100.0% |
| Managers | 4 | 100.0% |
| Models and fields | 8 | 100.0% |
| Query lookups | 4 | 100.0% |
| Querysets and managers | 9 | 100.0% |
| Relations | 5 | 100.0% |
| Settings and metadata | 2 | 100.0% |

## Feature Matrix

| Area | Capability | Contract cases | Contract coverage | Mypy agreement | Official Django documentation |
| --- | --- | ---: | ---: | ---: | --- |
| Models and fields | `models.subclass-transform` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/topics/db/models/) |
| Models and fields | `models.default-primary-key` | 2/2 | 100.0% | 0.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/instances/#auto-incrementing-primary-keys) |
| Models and fields | `models.field-descriptors` | 3/3 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/fields/) |
| Models and fields | `models.constructor-keywords` | 7/7 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/instances/) |
| Models and fields | `models.create-keywords` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#create) |
| Models and fields | `models.abstract-proxy-inheritance` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/topics/db/models/#model-inheritance) |
| Models and fields | `models.choices-enums` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/fields/#enumeration-types) |
| Models and fields | `models.custom-fields` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/howto/custom-model-fields/) |
| Relations | `relations.foreign-key-one-to-one` | 3/3 | 100.0% | 66.7% | [Django documentation](https://docs.djangoproject.com/en/6.1/topics/db/queries/#lookups-that-span-relationships) |
| Relations | `relations.many-to-many` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/topics/db/queries/#lookups-that-span-relationships) |
| Relations | `relations.reverse-relations` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/topics/db/queries/#lookups-that-span-relationships) |
| Relations | `relations.string-settings-targets` | 3/3 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/topics/db/queries/#lookups-that-span-relationships) |
| Relations | `relations.related-query-name` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/topics/db/queries/#lookups-that-span-relationships) |
| Managers | `managers.default-manager` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/topics/db/managers/) |
| Managers | `managers.declared-manager` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/topics/db/managers/) |
| Managers | `managers.custom-queryset-methods` | 3/3 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/topics/db/managers/) |
| Managers | `managers.from-queryset-as-manager` | 4/4 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/topics/db/managers/) |
| Querysets and managers | `querysets.chain-preserving-methods` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/querysets/) |
| Querysets and managers | `querysets.scalar-return-methods` | 3/3 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/querysets/) |
| Querysets and managers | `querysets.async-return-methods` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/querysets/) |
| Querysets and managers | `querysets.values` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/querysets/) |
| Querysets and managers | `querysets.values-list` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/querysets/) |
| Querysets and managers | `querysets.annotate` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/querysets/) |
| Querysets and managers | `querysets.prefetch-annotations` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#prefetch-related) |
| Querysets and managers | `querysets.ordering-field-validation` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#order-by) |
| Querysets and managers | `querysets.bulk-operations` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#bulk-update) |
| Query lookups | `lookups.field-traversal` | 2/2 | 100.0% | 50.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/querysets/) |
| Query lookups | `lookups.value-validation` | 12/12 | 100.0% | 91.7% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#field-lookups) |
| Query lookups | `lookups.creation-defaults` | 17/17 | 100.0% | 47.1% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#get-or-create) |
| Query lookups | `lookups.selected-field-validation` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#values) |
| Settings and metadata | `settings.project-settings-types` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/topics/settings/) |
| Settings and metadata | `metadata.get-field` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/meta/) |
| Django extras | `forms.model-forms` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/topics/forms/modelforms/) |
| Django extras | `auth.user-model` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/topics/auth/customizing/#referencing-the-user-model) |
| Django extras | `models.save-update-fields` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/instances/#specifying-which-fields-to-save) |
| Django extras | `http.querydict-mutability` | 6/6 | 100.0% | 66.7% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/request-response/#querydict-objects) |
| Django extras | `typing.lazy-string` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/topics/i18n/translation/#lazy-translation) |
| Django extras | `apps.model-registry` | 4/4 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/applications/#django.apps.apps.get_model) |

## Reproduce

```sh
bash scripts/differential-conformance.sh --check
uv run --no-project --python 3.11 python scripts/evaluate_django_stubs_coverage.py --check
```

To additionally verify the vendored files against the pinned source checkout:

```sh
uv run --no-project --python 3.11 python scripts/evaluate_django_stubs_coverage.py --upstream-root /path/to/django-stubs-6.1.1 --check
```

The differential runner builds both environments, validates every declared official-documentation outcome and runtime proof, rejects diagnostics outside assertion markers, and compares accept/reject behavior line by line. The documentation check verifies the vendored static tree, source inventory, checked result, and generated report.
