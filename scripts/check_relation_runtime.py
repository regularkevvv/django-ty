"""Check relation object/key behavior against real Django and in-memory SQLite."""

from __future__ import annotations

import json
from uuid import UUID

import django
from django.conf import settings


def main() -> None:
    settings.configure(
        INSTALLED_APPS=[],
        DATABASES={
            "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
        },
        DEFAULT_AUTO_FIELD="django.db.models.AutoField",
    )
    django.setup()
    from django.db import connection, models

    class TextKey(models.Model):
        slug = models.CharField(primary_key=True, max_length=30)

        class Meta:
            app_label = "relation_probe"

    class TextChild(TextKey):
        class Meta:
            app_label = "relation_probe"

    class UuidKey(models.Model):
        key = models.UUIDField(primary_key=True)

        class Meta:
            app_label = "relation_probe"

    class CodeKey(models.Model):
        code = models.CharField(max_length=30, unique=True)

        class Meta:
            app_label = "relation_probe"

    class Ref(models.Model):
        text = models.ForeignKey(TextKey, on_delete=models.CASCADE)
        uuid = models.ForeignKey(UuidKey, null=True, on_delete=models.CASCADE)
        code = models.ForeignKey(CodeKey, to_field="code", on_delete=models.CASCADE)

        class Meta:
            app_label = "relation_probe"

    class AbstractBase(models.Model):
        zeta = models.CharField(max_length=30)

        class Meta:
            abstract = True
            app_label = "relation_probe"

    class AbstractChild(AbstractBase):
        alpha = models.IntegerField()

        class Meta:
            app_label = "relation_probe"

    class ProxyText(TextKey):
        class Meta:
            proxy = True
            app_label = "relation_probe"

    class ExplicitChild(TextKey):
        parent = models.OneToOneField(
            TextKey, parent_link=True, primary_key=True, on_delete=models.CASCADE
        )
        extra = models.IntegerField(default=7)

        class Meta:
            app_label = "relation_probe"

    class LateChild(TextKey):
        extra = models.IntegerField(default=11)
        link = models.OneToOneField(
            TextKey, parent_link=True, primary_key=True, on_delete=models.CASCADE
        )

        class Meta:
            app_label = "relation_probe"

    with connection.schema_editor() as editor:
        for model in [
            TextKey,
            TextChild,
            UuidKey,
            CodeKey,
            Ref,
            AbstractChild,
            ExplicitChild,
            LateChild,
        ]:
            editor.create_model(model)
    key = UUID("12345678-1234-5678-1234-567812345678")
    text = TextKey.objects.create(slug="alpha")
    uuid = UuidKey.objects.create(key=key)
    code = CodeKey.objects.create(code="beta")
    row = Ref.objects.create(text=text, uuid=uuid, code=code)
    nullable = Ref.objects.create(text=text, code=code)
    child = TextChild.objects.create(slug="child")
    Ref.objects.create(text=child, code=code)
    abstract_child = AbstractChild.objects.create(zeta="zeta", alpha=9)
    explicit_child = ExplicitChild.objects.create(parent=text, slug="alpha", extra=7)
    late_child = LateChild.objects.create(link=text, slug="alpha", extra=11)
    checks = {
        "object_constructor_sets_text_key": Ref(text=text).text_id == "alpha",
        "raw_constructor_keeps_text_key": Ref(text_id="alpha").text_id == "alpha",
        "stored_text_key": Ref.objects.get(pk=row.pk).text_id == "alpha",
        "stored_uuid_key": Ref.objects.get(pk=row.pk).uuid_id == key,
        "stored_to_field_key": Ref.objects.get(pk=row.pk).code_id == "beta",
        "filter_by_text_key": Ref.objects.filter(text="alpha").count() == 2,
        "filter_by_to_field_key": Ref.objects.filter(code="beta").count() == 3,
        "values_returns_raw_keys": Ref.objects.values("text", "code", "uuid").get(
            pk=row.pk
        )
        == {"text": "alpha", "code": "beta", "uuid": key},
        "values_list_returns_raw_keys": Ref.objects.values_list("text", "code").get(
            pk=row.pk
        )
        == ("alpha", "beta"),
        "values_traverses_relation": Ref.objects.values("text__slug").get(pk=row.pk)[
            "text__slug"
        ]
        == "alpha",
        "nullable_join_returns_none": Ref.objects.values("uuid__key").get(
            pk=nullable.pk
        )["uuid__key"]
        is None,
        "default_values_uses_concrete_attribute_names": Ref.objects.values().get(
            pk=row.pk
        )
        == {"id": row.pk, "text_id": "alpha", "uuid_id": key, "code_id": "beta"},
        "default_values_omits_pk_alias": "pk"
        not in Ref.objects.values().get(pk=row.pk),
        "default_values_omits_relation_alias": "text"
        not in Ref.objects.values().get(pk=row.pk),
        "default_values_list_preserves_declaration_order": Ref.objects.values_list().get(
            pk=row.pk
        )
        == (row.pk, "alpha", key, "beta"),
        "default_values_list_flat_uses_first_column": Ref.objects.values_list(
            flat=True
        ).get(pk=row.pk)
        == row.pk,
        "default_values_list_named_uses_attribute_names": Ref.objects.values_list(
            named=True
        )
        .get(pk=row.pk)
        ._fields
        == ("id", "text_id", "uuid_id", "code_id"),
        "default_custom_pk_row_has_no_extra_alias": TextKey.objects.values_list().get(
            pk=text.pk
        )
        == ("alpha",),
        "default_inherited_row_includes_parent_pointer": TextChild.objects.values_list().get(
            pk=child.pk
        )
        == ("child", "child"),
        "abstract_fields_follow_implicit_key": AbstractChild.objects.values_list().get(
            pk=abstract_child.pk
        )
        == (abstract_child.pk, "zeta", 9),
        "proxy_rows_match_concrete_parent": ProxyText.objects.values_list().get(
            pk=text.pk
        )
        == ("alpha",),
        "explicit_parent_link_replaces_generated_link": ExplicitChild.objects.values_list().get(
            pk=explicit_child.pk
        )
        == ("alpha", "alpha", 7),
        "explicit_parent_link_column_names": tuple(
            ExplicitChild.objects.values().get(pk=explicit_child.pk)
        )
        == ("slug", "parent_id", "extra"),
        "explicit_parent_link_keeps_declared_order": LateChild.objects.values_list().get(
            pk=late_child.pk
        )
        == ("alpha", 11, "alpha"),
        "late_parent_link_named_columns": LateChild.objects.values_list(named=True)
        .get(pk=late_child.pk)
        ._fields
        == ("slug", "extra", "link_id"),
        "filter_accepts_model_subclass": Ref.objects.filter(text=child).count() == 1,
        "assignment_accepts_model_subclass": Ref(text=child).text is child,
    }
    try:
        Ref(text=1)
        checks["integer_relation_constructor_rejected"] = False
    except ValueError:
        checks["integer_relation_constructor_rejected"] = True
    try:
        row.text = 1
        checks["integer_relation_assignment_rejected"] = False
    except ValueError:
        checks["integer_relation_assignment_rejected"] = True
    try:
        Ref.objects.filter(text=uuid)
        checks["unrelated_model_filter_rejected"] = False
    except ValueError:
        checks["unrelated_model_filter_rejected"] = True
    try:
        Ref(text=uuid)
        checks["unrelated_model_assignment_rejected"] = False
    except ValueError:
        checks["unrelated_model_assignment_rejected"] = True
    assert all(checks.values()), checks
    print(
        json.dumps(
            {"django": django.get_version(), "cases": checks, "passed": True}, indent=2
        )
    )


if __name__ == "__main__":
    main()
