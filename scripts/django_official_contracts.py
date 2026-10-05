"""Version-specific official references and reviewed checker disagreements."""

from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "compatibility/django-official-contracts.toml"


def load_contracts() -> dict:
    with CONTRACT_PATH.open("rb") as file:
        return tomllib.load(file)


def documentation_url(
    django: str, feature: str, contracts: dict, route: str | None = None
) -> str:
    minor = ".".join(django.split(".")[:2])
    route = route or contracts["feature_docs"][feature]
    if route.startswith("/") or ":" in route or ".." in route:
        raise ValueError(f"invalid official documentation route: {route}")
    return f"https://docs.djangoproject.com/en/{minor}/{route}"


def reviewed_difference(
    feature: str, case: str, expect: str, django: str, runtime: dict, contracts: dict
) -> dict:
    identity = f"{feature}/{case}"
    review = contracts["review"].get(identity)
    if review is None or review["expect"] != expect:
        raise ValueError(
            f"unreviewed mypy disagreement: {identity}; check Django's official documentation and add a runtime proof"
        )
    evidence = runtime["cases"].get(review["proof"])
    if (
        not evidence
        or evidence.get("passed") is not True
        or runtime["django"] != django
    ):
        raise ValueError(
            f"missing successful Django {django} runtime proof for {identity}"
        )
    result = {
        "classification": review["classification"],
        "documentation": documentation_url(
            django, feature, contracts, review.get("documentation")
        ),
        "runtime_proof": review["proof"],
    }
    if "source" in review:
        result["django_source"] = (
            f"https://github.com/django/django/blob/{django}/{review['source']}"
        )
    return result
