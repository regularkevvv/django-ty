# Django Compatibility Map

MyPy comparison baseline: [`django-stubs` 6.1.2](https://github.com/typeddjango/django-stubs/tree/fa03b48b8cdfe336065f5ad8eb51fbcc40c6b1d2) at `fa03b48b8cdfe336065f5ad8eb51fbcc40c6b1d2`.

The wheel packages `django-types==0.24.0` declarations with reviewed modern Django module restorations and adapters. Exact input and output hashes and every adapter are recorded in [`native-types-vendor.json`](../compatibility/native-types-vendor.json). It neither installs nor executes the upstream mypy plugin.

Reviewed adapters preserve current authentication, storage, request and field declarations. Custom request subclasses retain their identity; framework request types stay immutable. The reproducible provider check verifies the complete tree before regeneration, and scripts/check_querydict_runtime.py compares nine assignment cases with the installed Django runtime.

## Measured Surface

- Vendored static declaration inventory: 730 `.pyi` modules and 16664 public symbols are packaged in the wheel.
- Vendored static-tree SHA-256: `0da8604a06078b639ed419e6681f2dd36d22b134baefb96328f3ae9ab6acc560`.
- Inventory counts include imported typing names and explicit inherited declarations; they are provenance controls, not a percentage of all Django APIs. Semantic coverage below measures the reviewed documentation contracts.
- Documented feature contract coverage: **100.0%** across 39 reviewed capabilities (39 supported, 0 partial, 0 unsupported).
- Assertion conformance: **100.0%** (172 of 172 documented expectations matched).
- Candidate host: `django-ty` 0.8.0 on `ty-extended` 0.90.0 at `503f4228e69946d4c652e8a5485916a850b7bd16`.
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
| Querysets and managers | 10 | 100.0% |
| Relations | 5 | 100.0% |
| Settings and metadata | 2 | 100.0% |

## Feature Matrix

| Area | Capability | Contract cases | Contract coverage | Mypy agreement | Official Django documentation |
| --- | --- | ---: | ---: | ---: | --- |
| Models and fields | `models.subclass-transform` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/topics/db/models/) |
| Models and fields | `models.default-primary-key` | 49/49 | 100.0% | 42.9% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/instances/#auto-incrementing-primary-keys) |
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
| Settings and metadata | `metadata.get-field` | 2/2 | 100.0% | 50.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/meta/) |
| Django extras | `forms.model-forms` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/topics/forms/modelforms/) |
| Django extras | `auth.user-model` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/topics/auth/customizing/#referencing-the-user-model) |
| Django extras | `models.save-update-fields` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/instances/#specifying-which-fields-to-save) |
| Django extras | `http.querydict-mutability` | 6/6 | 100.0% | 66.7% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/request-response/#querydict-objects) |
| Django extras | `typing.lazy-string` | 2/2 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/topics/i18n/translation/#lazy-translation) |
| Django extras | `apps.model-registry` | 4/4 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/applications/#django.apps.apps.get_model) |
| Querysets and managers | `querysets.lazy-rows` | 6/6 | 100.0% | 100.0% | [Django documentation](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#values) |

## Reproduce

```sh
bash scripts/differential-conformance.sh --check
uv run --no-project --python 3.11 python scripts/evaluate_django_stubs_coverage.py --check
```

To additionally reproduce the packaged declaration tree from the pinned distribution inputs:

```sh
python scripts/vendor_native_django.py --django-types-root /path/to/django-types-0.24.0/django-stubs --legacy-root /path/to/django-ty-0.7.0/django_ty/stubs/django
```

The differential runner builds both environments, validates every declared official-documentation outcome and runtime proof, rejects diagnostics outside assertion markers, and compares accept/reject behavior line by line. The documentation check verifies the vendored static tree, source inventory, checked result, and generated report.
