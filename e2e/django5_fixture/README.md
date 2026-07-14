# Django 5 fixture

This fixture runs `django-ty` against a real Django 5.x installation instead of
the package-local fake Django module.

The positive pass covers model field descriptors, constructor keyword typing,
relation IDs, nullable relations, reverse relations, custom managers,
querysets, `values()`, `values_list()`, `annotate()`, and common queryset
preserving methods.

The negative pass intentionally exercises unknown relation targets, duplicate
reverse relations, invalid constructor values, invalid assignments, bad lookup
value types, unknown lookup names, relation lookup traversal, `values()`, and
`values_list()`.

Run it with:

```sh
scripts/e2e_django5.sh
```
