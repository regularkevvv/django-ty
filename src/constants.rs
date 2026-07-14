pub const MODEL_BASES: &[&str] = &[
    "django.db.models.base.Model",
    "django.db.models.Model",
    "django.db.models.base.ModelBase.__call__",
];

pub const BASE_MANAGER_BASE: &str = "django.db.models.manager.BaseManager";
pub const MANAGER_BASE: &str = "django.db.models.manager.Manager";
pub const QUERYSET_BASE: &str = "django.db.models.query.QuerySet";
pub const OPTIONS_BASE: &str = "django.db.models.options.Options";
pub const CHOICES_BASES: &[&str] = &[
    "django.db.models.enums.Choices",
    "django.db.models.enums.TextChoices",
    "django.db.models.enums.IntegerChoices",
];

pub const MANAGER_METHODS: &[&str] = &[
    "all",
    "filter",
    "exclude",
    "complex_filter",
    "get",
    "create",
    "bulk_create",
    "bulk_update",
    "get_or_create",
    "update_or_create",
    "first",
    "last",
    "earliest",
    "latest",
    "count",
    "exists",
    "values",
    "values_list",
    "annotate",
    "alias",
    "order_by",
    "distinct",
    "none",
    "only",
    "defer",
    "select_related",
    "prefetch_related",
    "select_for_update",
    "reverse",
    "using",
    "union",
    "intersection",
    "difference",
    "aget",
    "acreate",
    "aget_or_create",
    "aupdate_or_create",
    "afirst",
    "alast",
    "acount",
    "aexists",
];

pub const LOOKUP_METHODS: &[&str] = &[
    "filter",
    "exclude",
    "get",
    "get_or_create",
    "update_or_create",
    "aget",
    "aget_or_create",
    "aupdate_or_create",
];

pub const FIELD_NAME_METHODS: &[&str] =
    &["order_by", "distinct", "only", "defer", "select_related"];

pub const QUERYSET_RETURNING_METHODS: &[&str] = &[
    "all",
    "filter",
    "exclude",
    "complex_filter",
    "order_by",
    "distinct",
    "none",
    "only",
    "defer",
    "select_related",
    "prefetch_related",
    "select_for_update",
    "reverse",
    "using",
    "union",
    "intersection",
    "difference",
    "alias",
];
