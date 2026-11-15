# django-ty

Django ORM support for [ty-extended](https://github.com/regularkevvv/ty-extended).
Plugins use the Python subset supported by Monty.

**This repository moved.** Development now lives in the ty-extended repository at
[`plugins/django-ty`](https://github.com/regularkevvv/ty-extended/tree/main/plugins/django-ty),
which also publishes the `django-ty` PyPI package. This copy is archived
read-only; file issues and pull requests in
[ty-extended](https://github.com/regularkevvv/ty-extended).

## Install and check

```sh
uv add django-ty "ty-extended>=0.91.0,<1.0"
```

```toml
# pyproject.toml
[tool.ty.plugins]
auto-discover = true
```

```sh
tyx check .
```
