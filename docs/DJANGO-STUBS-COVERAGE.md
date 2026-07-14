# Django Compatibility Map

Static declaration baseline: [`django-stubs` 6.0.6](https://github.com/typeddjango/django-stubs/tree/c1d968a356955f9598da6536115ccae4ed802b44) at `c1d968a356955f9598da6536115ccae4ed802b44`.

`django-ty` vendors the pinned declaration tree inside its wheel. It neither installs nor executes the upstream mypy plugin.

## Measured Surface

- Static API: **100% available**: 704 `.pyi` modules and 16569 public symbols are packaged in the wheel.
- Vendored static-tree SHA-256: `ddd7f5058ccd5cad6590adf121b033a7809b68bcd83ca14103d7ff070423aba6`.
- Dynamic feature-balanced parity: **100.0%** across 37 reference capabilities (37 supported, 0 partial, 0 unsupported).
- Assertion conformance: **100.0%** (82 of 82 reference outcomes matched).
- Candidate host: `django-ty` 0.1.1 on `ty-extended` 0.59.0 at `384acfd51695dc5eb9e8af8c166da961a1095a40`.
- Target: **95%** dynamic semantic parity. The static score is deliberately separate and does not hide semantic gaps.

Auxiliary `django-stubs-ext` utilities such as `WithAnnotations` are outside this Django-behavior inventory. The candidate wheel must not install or package `django-stubs`, `django-stubs-ext`, or mypy; generic `Annotated` transport remains a library-neutral ty-extended plugin capability.

## Methodology

The inventory maps every transformer module in the pinned django-stubs plugin to reviewed capabilities. Each capability has at least two line-level assertions in one shared Django project.

Pinned mypy plus django-stubs is the reference oracle. Every assertion declares whether the reference must accept or reject it; disagreement invalidates the corpus. ty then checks the identical files. A match means both checkers made the same accept/reject decision on that assertion line. Diagnostics on unmarked lines invalidate the run instead of affecting the score indirectly.

Feature-balanced parity gives every capability equal weight. Assertion conformance reports the raw matched assertions. Diagnostic wording is retained as evidence but is not compared, because the checkers use different rule names and messages.

## Dynamic Coverage

| Area | Capabilities | Feature-balanced parity |
| --- | ---: | ---: |
| Django extras | 5 | 100.0% |
| Managers | 4 | 100.0% |
| Models and fields | 8 | 100.0% |
| Query lookups | 4 | 100.0% |
| Querysets and managers | 9 | 100.0% |
| Relations | 5 | 100.0% |
| Settings and metadata | 2 | 100.0% |

## Feature Matrix

| Area | Capability | Cases matched | Parity | Status | Upstream reference |
| --- | --- | ---: | ---: | --- | --- |
| Models and fields | `models.subclass-transform` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/models.py:process_model_class` |
| Models and fields | `models.default-primary-key` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/models.py:AddDefaultPrimaryKey<br>mypy_django_plugin/transformers/models.py:AddPrimaryKeyAlias` |
| Models and fields | `models.field-descriptors` | 3/3 | 100.0% | supported | `mypy_django_plugin/transformers/fields.py:set_descriptor_types_for_field` |
| Models and fields | `models.constructor-keywords` | 3/3 | 100.0% | supported | `mypy_django_plugin/transformers/init_create.py:typecheck_model_init` |
| Models and fields | `models.create-keywords` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/init_create.py:typecheck_model_create<br>mypy_django_plugin/transformers/init_create.py:typecheck_model_acreate` |
| Models and fields | `models.abstract-proxy-inheritance` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/models.py:ModelClassInitializer` |
| Models and fields | `models.choices-enums` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/choices.py:transform_into_proper_attr_type` |
| Models and fields | `models.custom-fields` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/fields.py:transform_into_proper_return_type<br>mypy_django_plugin/transformers/fields.py:determine_type_of_array_field` |
| Relations | `relations.foreign-key-one-to-one` | 3/3 | 100.0% | supported | `mypy_django_plugin/transformers/models.py:AddRelatedModelsId<br>mypy_django_plugin/transformers/fields.py:fill_descriptor_types_for_related_field` |
| Relations | `relations.many-to-many` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/manytomany.py:refine_many_to_many_related_manager<br>mypy_django_plugin/transformers/models.py:ProcessManyToManyFields` |
| Relations | `relations.reverse-relations` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/models.py:AddReverseLookups<br>mypy_django_plugin/transformers/manytoone.py:refine_many_to_one_related_manager` |
| Relations | `relations.string-settings-targets` | 3/3 | 100.0% | supported | `mypy_django_plugin/django/context.py:model_class_fullnames_by_label` |
| Relations | `relations.related-query-name` | 2/2 | 100.0% | supported | `mypy_django_plugin/django/context.py:resolve_lookup_into_field` |
| Managers | `managers.default-manager` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/models.py:AddDefaultManagerAttribute` |
| Managers | `managers.declared-manager` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/models.py:AddManagers` |
| Managers | `managers.custom-queryset-methods` | 3/3 | 100.0% | supported | `mypy_django_plugin/transformers/managers.py:resolve_manager_method<br>mypy_django_plugin/transformers/querysets.py:merge_annotations_from_custom_method` |
| Managers | `managers.from-queryset-as-manager` | 4/4 | 100.0% | supported | `mypy_django_plugin/transformers/managers.py:create_new_manager_class_from_from_queryset_method<br>mypy_django_plugin/transformers/managers.py:add_as_manager_to_queryset_class` |
| Querysets and managers | `querysets.chain-preserving-methods` | 2/2 | 100.0% | supported | `mypy_django_plugin/main.py:manager_and_queryset_method_hooks` |
| Querysets and managers | `querysets.scalar-return-methods` | 3/3 | 100.0% | supported | `mypy_django_plugin/main.py:manager_and_queryset_method_hooks` |
| Querysets and managers | `querysets.async-return-methods` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/init_create.py:typecheck_model_acreate<br>mypy_django_plugin/main.py:manager_and_queryset_method_hooks` |
| Querysets and managers | `querysets.values` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/querysets.py:extract_proper_type_queryset_values` |
| Querysets and managers | `querysets.values-list` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/querysets.py:extract_proper_type_queryset_values_list` |
| Querysets and managers | `querysets.annotate` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/querysets.py:extract_proper_type_queryset_annotate` |
| Querysets and managers | `querysets.prefetch-annotations` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/querysets.py:extract_prefetch_related_annotations<br>mypy_django_plugin/transformers/querysets.py:specialize_prefetch_type` |
| Querysets and managers | `querysets.ordering-field-validation` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/querysets.py:validate_order_by<br>mypy_django_plugin/transformers/querysets.py:validate_defer_only<br>mypy_django_plugin/transformers/querysets.py:validate_select_related` |
| Querysets and managers | `querysets.bulk-operations` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/querysets.py:validate_bulk_create<br>mypy_django_plugin/transformers/querysets.py:validate_bulk_update` |
| Query lookups | `lookups.field-traversal` | 2/2 | 100.0% | supported | `mypy_django_plugin/django/context.py:resolve_lookup_into_field` |
| Query lookups | `lookups.value-validation` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/orm_lookups.py:typecheck_queryset_filter` |
| Query lookups | `lookups.creation-defaults` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/orm_lookups.py:_typecheck_defaults_kwarg` |
| Query lookups | `lookups.selected-field-validation` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/querysets.py:resolve_field_lookups` |
| Settings and metadata | `settings.project-settings-types` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/settings.py:get_type_of_settings_attribute` |
| Settings and metadata | `metadata.get-field` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/meta.py:return_proper_field_type_from_get_field` |
| Django extras | `forms.model-forms` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/forms.py:transform_form_class` |
| Django extras | `auth.user-model` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/auth.py:get_user_model<br>mypy_django_plugin/transformers/models.py:set_auth_user_model_boolean_fields` |
| Django extras | `models.save-update-fields` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/save.py:validate_save_update_fields` |
| Django extras | `http.querydict-mutability` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/request.py:check_querydict_is_mutable` |
| Django extras | `typing.lazy-string` | 2/2 | 100.0% | supported | `mypy_django_plugin/transformers/functional.py:resolve_str_promise_attribute` |

## Reproduce

```sh
bash scripts/differential-conformance.sh --check
uv run --no-project --python 3.11 python scripts/evaluate_django_stubs_coverage.py --check
```

To additionally verify the vendored files against the pinned source checkout:

```sh
uv run --no-project --python 3.11 python scripts/evaluate_django_stubs_coverage.py --upstream-root /path/to/django-stubs-6.0.6 --check
```

The differential runner builds both environments, validates every declared reference outcome, rejects diagnostics outside assertion markers, and compares accept/reject behavior line by line. The documentation check verifies the vendored static tree, source inventory, checked result, and generated report.
