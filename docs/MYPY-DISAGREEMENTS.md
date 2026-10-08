# Where django-ty and mypy disagree

Examples use the [test models](../conformance/conformance_models/models.py). “mypy” means mypy **with django-stubs and its Django plugin**. Version numbers below refer to **django-stubs**, unless stated otherwise.

The [original audit](../compatibility/mypy-disagreement-audit.json) records all 24 assertion disagreements, exact versions, diagnostics, source hashes, and reproductions. Cases with the same cause are grouped here. The [current matrix](DJANGO-VERSIONS.md) records the 0.5.0 candidate's results.

## Model IDs: tracked state versus nonnullable getters

```python
book = Book()                       # id/pk: None
book = Book(id=123)                  # id/pk: int, even before saving
book.save()                         # id/pk: int after successful save
alias = book
alias.delete()                      # book.id/book.pk: None
book = Book.objects.get(pk=1)        # id/pk: int
```

**Disagreement:** mypy keeps auto-ID getters nonnullable (`int`) even before saving and after deletion. django-ty 0.5.0 tracks auto-primary-key values using ty-extended **0.84.4+**. All five originally audited django-stubs releases use the nonnullable policy: 5.0.4, 5.1.3, 5.2.9, 6.0.6, and 6.1.1.

**Which is right?** django-ty follows Django's lifecycle. Mypy's nonnullable getter is a deliberate typing policy. Branches merge states; aliases share updates; unknown calls discard refinements. `save(update_fields=[])` does not establish an ID.

An auto key with [`db_default`](https://docs.djangoproject.com/en/6.1/ref/models/fields/#db-default) starts as `DatabaseDefault`; a successful save establishes `int`.

**Limits:** Custom initialization/loading, overridden methods, and uncertain arguments keep broad types. Non-auto keys, foreign-key IDs, concrete multi-table inheritance, async calls, and optional or container results are outside this refinement.

Concrete children use a separate [parent-link primary key](https://docs.djangoproject.com/en/6.1/topics/db/models/#multi-table-inheritance): `Child(id=123).pk` can be `None`. Abstract and proxy inheritance retain tracking.

**Callbacks:** Project `@receiver` handlers keep construction, loading, and saving broad for their sender models. Deletion still clears the ID. External handlers, aliased decorators, and dynamic registration require an opt-out when callbacks change IDs:

```toml
[tool.ty.plugins.config.django-ty]
model-state = false
```

**Evidence:** [Django primary-key docs](https://docs.djangoproject.com/en/6.1/ref/models/instances/#auto-incrementing-primary-keys), [skipped saves](https://docs.djangoproject.com/en/6.1/ref/models/instances/#specifying-which-fields-to-save), [deletion](https://docs.djangoproject.com/en/6.1/ref/models/instances/#deleting-objects), [runtime tests](../scripts/check_django_runtime_contracts.py), and [static lifecycle tests](../conformance/cases/model_state.py). [Django initialization](https://github.com/django/django/blob/249b13d6e93ee3164dee8ed1775395622a50c337/django/db/models/base.py#L502) sets field defaults; [mypy's explicit nonnullable getters](https://github.com/typeddjango/django-stubs/blob/c7816bcf4cb8ec8706acb5b671ca62131b345ef7/mypy_django_plugin/transformers/models.py#L274) follow [PR #634](https://github.com/typeddjango/django-stubs/pull/634).


## Fresh request parameters: deliberate workaround

```python
HttpRequest().GET["page"] = "1"   # Django accepts
HttpRequest().POST["page"] = "1"  # Django accepts
# A framework-created request's GET/POST are normally immutable.
```

**Disagreement:** django-ty accepts these fresh-instance writes; mypy with 6.1.1 rejects them.

**Which is right?** These exact writes are valid. Upstream deliberately keeps the base request annotation immutable and provides `django_stubs_ext.MutableHttpRequest` for this use case. Its earlier constructor hack lost custom subclass types.

**Evidence:** [QueryDict docs](https://docs.djangoproject.com/en/6.1/ref/request-response/#querydict-objects), [HttpRequest creates mutable dictionaries](https://github.com/django/django/blob/249b13d6e93ee3164dee8ed1775395622a50c337/django/http/request.py#L62), [subclass regression #3565](https://github.com/typeddjango/django-stubs/issues/3565), and [the upstream helper fix #3642](https://github.com/typeddjango/django-stubs/pull/3642).

**Our fix:** 0.4.0 had the same subclass regression. The 0.5.0 candidate uses an exact-class constructor hook, preserving custom subclass types and attributes. WSGI/ASGI immutability is tested separately.

## Callable defaults: upstream validation bug

```python
Author.objects.get_or_create(name="Ada", defaults={"age": lambda: 43})
Author.objects.update_or_create(name="Ada", defaults={"age": lambda: 44})
# Both are valid. Returning Book() instead of an integer is invalid.
```

**Disagreement:** mypy rejects the valid callables with 6.0.6, 6.0.9, and 6.1.1. Older 5.0.4/5.1.3/5.2.9 also miss invalid defaults, including `{"age": Book()}` and `{"age": lambda: Book()}`.

**Which is right?** django-ty matches Django: accept a valid callable's result and reject an incompatible result. Django evaluates the callable before creating or updating the model.

**Evidence:** Django's [get_or_create docs](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#get-or-create) and [update_or_create docs](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#update-or-create) permit callables. [Django resolves them](https://github.com/django/django/blob/249b13d6e93ee3164dee8ed1775395622a50c337/django/db/models/utils.py#L28); the [plugin compares the callable itself with the field type](https://github.com/typeddjango/django-stubs/blob/c7816bcf4cb8ec8706acb5b671ca62131b345ef7/mypy_django_plugin/transformers/orm_lookups.py#L59). [PR #3326](https://github.com/typeddjango/django-stubs/pull/3326) added defaults validation. Supported-version reproductions confirm the valid-callable rejection; no exact matching upstream issue was found in the audit.

**Our fix:** the 0.5.0 candidate checks lambda, named, and typed callable results, including create/update branches, `create_defaults`, and async APIs. Mixed dictionaries still use a combined value type, so validation is conservative rather than precise for every entry. The published mypy plugin remains unmodified.

## Invalid related lookup: missed path validation

```python
Category.objects.filter(parent__missing__exact=1)  # Invalid path
```

**Disagreement:** all five originally audited plugins accept this; django-ty rejects it.

**Which is right?** django-ty. Django raises `FieldError` for the unknown `missing` transform before checking the value. The plugin checks the final `exact` lookup but misses the intermediate transform.

**Evidence:** [Django lookup docs](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#field-lookups), [Django's transform validation](https://github.com/django/django/blob/249b13d6e93ee3164dee8ed1775395622a50c337/django/db/models/sql/query.py#L1460), and [the plugin's lookup resolution](https://github.com/typeddjango/django-stubs/blob/c7816bcf4cb8ec8706acb5b671ca62131b345ef7/mypy_django_plugin/django/context.py#L538). [PR #3655](https://github.com/typeddjango/django-stubs/pull/3655) improves known transform types; the inspected implementation still falls back when a transform is unknown.

**Our test fix:** the old example used `"x"`, letting newer mypy reject the value for the wrong reason. The candidate uses integer `1` and requires `django-ty.unknown-lookup`.

## `__in`: container type versus string contents

```python
Author.objects.filter(age__in=1)     # Invalid: integer is not iterable
Author.objects.filter(age__in="42")  # Valid: iterable characters coerce to integers
Author.objects.filter(age__in="x2")  # Invalid: "x" cannot become an integer
```

**Disagreement:** 5.0.4/5.1.3/5.2.9 miss the scalar-integer error. All five originally audited releases accept `"x2"`; django-ty rejects that known invalid literal.

**Which is right?** Rejecting `1` and `"x2"` matches Django. Mypy correctly recognizes that strings are iterable, but ordinary `str` typing cannot distinguish numeric from nonnumeric contents. This is a precision limit, not a reason to reject all strings.

**Evidence:** [Django `in` docs](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#in), [Django iterates and prepares values](https://github.com/django/django/blob/249b13d6e93ee3164dee8ed1775395622a50c337/django/db/models/lookups.py#L284), and [upstream's test deliberately accepts string contents](https://github.com/typeddjango/django-stubs/blob/c7816bcf4cb8ec8706acb5b671ca62131b345ef7/tests/typecheck/managers/querysets/test_filter.yml#L103). [PR #3314](https://github.com/typeddjango/django-stubs/pull/3314) fixed the iterable constraint; it did not add numeric-string validation.

## Older plugin gaps already fixed upstream

For these tested cases, django-ty matches Django. Newer audited plugins agree too. “Fixed by” identifies the upstream change and the first audited release containing it, not necessarily the first release ever shipping it.

| Disagreement | Correct behavior and Django evidence | Upstream fix / audited versions |
| --- | --- | --- |
| `apps.get_model("app.Book")` inferred as `type[Any]`; wrong-model assignments accepted | Infer `type[Book]` for the tested literal references, including keyword and case-insensitive model-name forms. [Docs](https://docs.djangoproject.com/en/6.1/ref/applications/#django.apps.apps.get_model) | [#3511](https://github.com/typeddjango/django-stubs/pull/3511); fixed in 6.0.9/6.1.1, absent from the original older pins. Dynamic names retain `Any`. |
| Custom manager methods inferred as `Any`, plus a stray `django-manager-missing` diagnostic | Preserve the copied method's queryset/scalar return type. [Docs](https://docs.djangoproject.com/en/6.1/topics/db/managers/#creating-a-manager-with-queryset-methods) | [#2377](https://github.com/typeddjango/django-stubs/pull/2377); fails in 5.0.4, fixed in 5.1.3 onward. A controlled backport removed both inference failures and the stray error. |
| Multiple-object `Prefetch(..., to_attr="books")` lacks `list[Book]` inference | The custom attribute contains a list. [Docs](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#prefetch-related) | [#2779](https://github.com/typeddjango/django-stubs/pull/2779), [#2786](https://github.com/typeddjango/django-stubs/pull/2786); fixed in 5.2.9 onward. |
| `Book(pk=1).save(update_fields=["missing"])` accepted | Reject the unknown field. [Docs](https://docs.djangoproject.com/en/6.1/ref/models/instances/#specifying-which-fields-to-save), [runtime validation](https://github.com/django/django/blob/249b13d6e93ee3164dee8ed1775395622a50c337/django/db/models/base.py#L841) | [#3444](https://github.com/typeddjango/django-stubs/pull/3444); fixed in 6.0.6 onward. |
| `Book.objects.order_by("missing")` accepted | Reject the unknown field. [Docs](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#order-by), [runtime validation](https://github.com/django/django/blob/249b13d6e93ee3164dee8ed1775395622a50c337/django/db/models/sql/query.py#L2326) | [#3158](https://github.com/typeddjango/django-stubs/pull/3158); fixed in 6.0.6 onward. |
| `Book.objects.only("missing")` accepted | Reject the unknown field. Django fails when the query is compiled, so the proof forces compilation. [Docs](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#only), [runtime validation](https://github.com/django/django/blob/249b13d6e93ee3164dee8ed1775395622a50c337/django/db/models/sql/query.py#L860) | [#3165](https://github.com/typeddjango/django-stubs/pull/3165); fixed in 6.0.6 onward. |
| `Book.objects.bulk_update([Book(pk=1)], ["missing"])` accepted | Reject the unknown field; supplying a primary key isolates this check. [Docs](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#bulk-update), [runtime validation](https://github.com/django/django/blob/249b13d6e93ee3164dee8ed1775395622a50c337/django/db/models/query.py#L991) | [#2808](https://github.com/typeddjango/django-stubs/pull/2808); fixed in 5.2.9 onward. |

## Evidence limits and remaining checks

- The original audit includes unsupported comparator combinations. The current [support catalog](../compatibility/reference-support.toml) prevents them: Django 5.2/6.0 use django-stubs 6.0.9 with mypy 2.3.1; upstream calls Django 5.2 support **partial**. [Upstream support table](https://github.com/typeddjango/django-stubs/blob/942bca5e63f897a157f5d8ee649ca90e9a69003b/README.md)
- Auto-key lifecycle tests cover explicit/inherited fields and row results. Custom primary keys and foreign-key ID state remain outside this refinement.
- Migration models need a regression test. Upstream [excludes `StateApps`](https://github.com/typeddjango/django-stubs/blob/c7816bcf4cb8ec8706acb5b671ca62131b345ef7/mypy_django_plugin/main.py#L263) because historical schemas must not resolve to current model classes. This audit identifies an unverified django-ty boundary, not a demonstrated failure. Custom app-label inference is also limited.
