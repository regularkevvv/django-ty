use django_ty::DjangoTyPlugin;
use ty_plugin_sdk::Plugin;
use ty_plugin_sdk::protocol::{
    AnalyzeClassRequest, ArgumentKind, ArgumentSummary, AssignedValueSummary, AssignmentSummary,
    BuildProjectIndexRequest, CallRequest, CallReturnPatch, CallSignaturePatch, CallValueSummary,
    ClassSummary, ContributionPatch, FieldSummary, LiteralDictEntry, LiteralValue,
    MemberAccessPatch, MethodClaimKind, MethodSummary, MutationOperation, MutationRequest,
    NestedClassSummary, Parameter, ParameterKind, PluginRequest, PluginResponse, ProjectContext,
    ReceiverSummary, SemanticContext, SettingValueSummary, SettingsModuleSummary, SymbolRef,
    SymbolSource, TextPosition, TypeExpr, TypeSnapshot, ValueSummary, VirtualTypeShape,
};
use ty_plugin_sdk::serde_json::{Value, json};

const USER: &str = "accounts.models.User";
const AUTHOR: &str = "library.models.Author";
const BOOK: &str = "library.models.Book";
const TAG: &str = "library.models.Tag";

fn semantic_context(module: &str) -> SemanticContext {
    SemanticContext {
        module: module.to_string(),
        file_path: format!("/project/{}.py", module.replace('.', "/")),
        python_version: "3.13".to_string(),
        platform: "linux".to_string(),
        speculative: false,
    }
}

fn project_context() -> ProjectContext {
    ProjectContext {
        root: "/project".to_string(),
        python_version: "3.13".to_string(),
        platform: "linux".to_string(),
        config: json!({}),
    }
}

fn source(path: &str, line: u32) -> SymbolSource {
    SymbolSource {
        module: None,
        qualified_name: None,
        file_path: Some(path.to_string()),
        start: Some(TextPosition { line, column: 1 }),
        end: Some(TextPosition { line, column: 8 }),
    }
}

fn model_class(name: &str, fields: Vec<FieldSummary>) -> ClassSummary {
    ClassSummary {
        qualified_name: name.to_string(),
        bases: vec![TypeExpr::expression("django.db.models.base.Model")],
        decorators: Vec::new(),
        metaclass: None,
        fields,
        methods: Vec::new(),
        nested_classes: Vec::new(),
        class_constants: Vec::new(),
        source: source("/project/models.py", 1),
    }
}

fn derived_model_class(name: &str, base: &str, fields: Vec<FieldSummary>) -> ClassSummary {
    let mut class = model_class(name, fields);
    class.bases = vec![TypeExpr::expression(base)];
    class
}

fn non_model_class() -> ClassSummary {
    ClassSummary {
        qualified_name: "plain.Thing".to_string(),
        bases: vec![TypeExpr::expression("object")],
        decorators: Vec::new(),
        metaclass: None,
        fields: Vec::new(),
        methods: Vec::new(),
        nested_classes: Vec::new(),
        class_constants: Vec::new(),
        source: SymbolSource::default(),
    }
}

fn field(name: &str, callee: &str, arguments: Vec<ArgumentSummary>) -> FieldSummary {
    FieldSummary {
        name: name.to_string(),
        annotation: None,
        assigned_value: Some(AssignedValueSummary::Call(CallValueSummary {
            callee: SymbolRef {
                qualified_name: callee.to_string(),
            },
            receiver: None,
            arguments,
            return_type: None,
        })),
        inferred_type: None,
        has_default: false,
        source: source("/project/models.py", 10),
    }
}

fn scalar_field(name: &str, class_name: &str) -> FieldSummary {
    field(name, &format!("django.db.models.{class_name}"), Vec::new())
}

fn literal_assignment_field(name: &str) -> FieldSummary {
    FieldSummary {
        name: name.to_string(),
        annotation: None,
        assigned_value: Some(AssignedValueSummary::Literal {
            value: LiteralValue::Int { value: 1 },
        }),
        inferred_type: None,
        has_default: false,
        source: source("/project/models.py", 11),
    }
}

fn positional_str(value: &str) -> ArgumentSummary {
    ArgumentSummary {
        name: None,
        kind: ArgumentKind::Positional,
        type_expr: Some(TypeExpr::annotation("str")),
        value: LiteralValue::Str {
            value: value.to_string(),
        },
        source: None,
    }
}

fn positional_class(value: &str) -> ArgumentSummary {
    ArgumentSummary {
        name: None,
        kind: ArgumentKind::Positional,
        type_expr: Some(TypeExpr::annotation(value)),
        value: LiteralValue::ClassRef(SymbolRef {
            qualified_name: value.to_string(),
        }),
        source: None,
    }
}

fn positional_setting(value: &str) -> ArgumentSummary {
    ArgumentSummary {
        name: None,
        kind: ArgumentKind::Positional,
        type_expr: None,
        value: LiteralValue::EnumRef(SymbolRef {
            qualified_name: value.to_string(),
        }),
        source: None,
    }
}

fn keyword_bool(name: &str, value: bool) -> ArgumentSummary {
    ArgumentSummary {
        name: Some(name.to_string()),
        kind: ArgumentKind::Keyword,
        type_expr: Some(TypeExpr::annotation("bool")),
        value: LiteralValue::Bool { value },
        source: None,
    }
}

fn keyword_str(name: &str, value: &str) -> ArgumentSummary {
    ArgumentSummary {
        name: Some(name.to_string()),
        kind: ArgumentKind::Keyword,
        type_expr: Some(TypeExpr::annotation("str")),
        value: LiteralValue::Str {
            value: value.to_string(),
        },
        source: None,
    }
}

fn keyword_int(name: &str, value: i64) -> ArgumentSummary {
    ArgumentSummary {
        name: Some(name.to_string()),
        kind: ArgumentKind::Keyword,
        type_expr: Some(TypeExpr::annotation("int")),
        value: LiteralValue::Int { value },
        source: Some(source("/project/use.py", 4)),
    }
}

fn keyword_value(name: &str, value: LiteralValue) -> ArgumentSummary {
    ArgumentSummary {
        name: Some(name.to_string()),
        kind: ArgumentKind::Keyword,
        type_expr: None,
        value,
        source: Some(source("/project/use.py", 4)),
    }
}

fn keyword_list(name: &str, items: Vec<LiteralValue>) -> ArgumentSummary {
    keyword_value(name, LiteralValue::List { items })
}

fn positional_list(items: Vec<LiteralValue>) -> ArgumentSummary {
    ArgumentSummary {
        name: None,
        kind: ArgumentKind::Positional,
        type_expr: None,
        value: LiteralValue::List { items },
        source: Some(source("/project/use.py", 4)),
    }
}

fn settings() -> Vec<SettingsModuleSummary> {
    vec![SettingsModuleSummary {
        module: "settings".to_string(),
        values: vec![
            SettingValueSummary {
                name: "IGNORED_NUMBER".to_string(),
                value: LiteralValue::Int { value: 1 },
                source: SymbolSource::default(),
            },
            SettingValueSummary {
                name: "AUTH_USER_MODEL".to_string(),
                value: LiteralValue::Str {
                    value: "accounts.User".to_string(),
                },
                source: SymbolSource::default(),
            },
            SettingValueSummary {
                name: "SITE_NAME".to_string(),
                value: LiteralValue::Str {
                    value: "Library".to_string(),
                },
                source: SymbolSource::default(),
            },
        ],
        dependencies: Vec::new(),
        diagnostics: Vec::new(),
        source: SymbolSource::default(),
    }]
}

fn build_index(classes: Vec<ClassSummary>) -> PluginResponse {
    DjangoTyPlugin.build_project_index(&BuildProjectIndexRequest {
        context: project_context(),
        classes,
        settings: settings(),
        assignments: Vec::new(),
        previous_index_fingerprint: None,
    })
}

fn project_index(classes: Vec<ClassSummary>) -> Value {
    match build_index(classes) {
        PluginResponse::ProjectIndex(index) => index.plugin_index,
        other => panic!("expected project index, got {other:?}"),
    }
}

fn relation_field(
    name: &str,
    callee: &str,
    target: ArgumentSummary,
    extra: Vec<ArgumentSummary>,
) -> FieldSummary {
    let mut arguments = vec![target, positional_str("django.db.models.CASCADE")];
    arguments.extend(extra);
    field(name, &format!("django.db.models.{callee}"), arguments)
}

fn book_model() -> ClassSummary {
    model_class(
        BOOK,
        vec![
            scalar_field("title", "CharField"),
            field(
                "pages",
                "django.db.models.IntegerField",
                vec![
                    keyword_bool("null", true),
                    keyword_value("default", LiteralValue::Int { value: 100 }),
                ],
            ),
            relation_field(
                "author",
                "ForeignKey",
                positional_class(AUTHOR),
                vec![keyword_str("related_name", "books")],
            ),
            relation_field(
                "owner",
                "ForeignKey",
                positional_setting("django.conf.settings.AUTH_USER_MODEL"),
                vec![keyword_bool("null", true)],
            ),
            relation_field("tags", "ManyToManyField", positional_str("Tag"), Vec::new()),
            field("objects", "library.models.BookManager", Vec::new()),
            literal_assignment_field("computed"),
        ],
    )
}

fn author_model() -> ClassSummary {
    model_class(AUTHOR, vec![scalar_field("name", "CharField")])
}

fn tag_model() -> ClassSummary {
    model_class(TAG, vec![scalar_field("label", "CharField")])
}

fn user_model() -> ClassSummary {
    model_class(USER, vec![scalar_field("email", "EmailField")])
}

fn analyze_book(index: Value) -> PluginResponse {
    DjangoTyPlugin.analyze_class(&AnalyzeClassRequest {
        context: semantic_context("library.models"),
        class: book_model(),
        project_index: Some(index),
    })
}

fn manager_receiver(model_name: &str) -> ReceiverSummary {
    ReceiverSummary {
        type_expr: TypeExpr::annotation(format!("django.db.models.manager.Manager[{model_name}]")),
        nominal_class: Some("django.db.models.manager.Manager".to_string()),
        generic_arguments: vec![TypeExpr::annotation(model_name)],
        plugin_metadata: json!({}),
    }
}

fn queryset_receiver(model_name: &str, row_name: &str) -> ReceiverSummary {
    ReceiverSummary {
        type_expr: TypeExpr::annotation(format!(
            "django.db.models.query.QuerySet[{model_name}, {row_name}]"
        )),
        nominal_class: Some("django.db.models.query.QuerySet".to_string()),
        generic_arguments: vec![
            TypeExpr::annotation(model_name),
            TypeExpr::annotation(row_name),
        ],
        plugin_metadata: json!({}),
    }
}

fn call(
    method_name: &str,
    receiver: ReceiverSummary,
    arguments: Vec<ArgumentSummary>,
    index: Value,
) -> PluginResponse {
    DjangoTyPlugin.adjust_call_return(&CallRequest {
        context: semantic_context("library.use"),
        callee: TypeExpr::expression(format!("django.db.models.manager.Manager.{method_name}")),
        receiver: Some(receiver),
        arguments,
        existing_signature: None,
        default_return_type: None,
        project_index: Some(index),
    })
}

fn return_patch(response: PluginResponse) -> CallReturnPatch {
    match response {
        PluginResponse::CallReturnPatch(patch) => patch,
        other => panic!("expected call return patch, got {other:?}"),
    }
}

fn signature_patch(response: PluginResponse) -> CallSignaturePatch {
    match response {
        PluginResponse::CallSignaturePatch(patch) => patch,
        other => panic!("expected call signature patch, got {other:?}"),
    }
}

#[test]
fn manifest_declares_django_orm_capabilities() {
    let manifest = DjangoTyPlugin.manifest();

    assert_eq!(manifest.id, "django-ty");
    assert!(manifest.capabilities.class_transform);
    assert!(manifest.capabilities.project_index);
    assert!(manifest.capabilities.cross_symbol_contributions);
    assert!(manifest.capabilities.settings_data);
    assert!(manifest.capabilities.virtual_types);
    assert!(manifest.capabilities.call_return);
    assert!(manifest.capabilities.call_signature);
    assert!(!manifest.capabilities.instance_member);
    assert!(
        manifest
            .claims
            .settings
            .iter()
            .any(|claim| claim.module == "settings")
    );
    assert!(manifest.claims.classes.iter().any(|claim| {
        matches!(
            &claim.kind,
            ty_plugin_sdk::protocol::ClassClaimKind::SubclassOf { base_qualified_name }
                if base_qualified_name == "django.db.models.base.Model"
        )
    }));
    assert!(manifest.claims.methods.iter().any(|claim| {
        matches!(
            &claim.kind,
            MethodClaimKind::OnSubclassOf {
                base_qualified_name,
                method_name,
            } if base_qualified_name == "django.db.models.query.QuerySet" && method_name == "filter"
        )
    }));
    assert!(manifest.claims.methods.iter().any(|claim| {
        matches!(
            &claim.kind,
            MethodClaimKind::Exact {
                class_qualified_name,
                method_name,
            } if class_qualified_name == "django.db.models.manager.BaseManager" && method_name == "from_queryset"
        )
    }));
}

#[test]
fn from_queryset_signature_accepts_custom_querysets_and_preserves_the_manager_class() {
    let receiver = ReceiverSummary {
        type_expr: TypeExpr::annotation(
            "type[django.db.models.manager.Manager[library.models.Book]]",
        ),
        nominal_class: Some("django.db.models.manager.Manager".to_string()),
        generic_arguments: vec![TypeExpr::annotation("library.models.Book")],
        plugin_metadata: json!({}),
    };
    let patch = signature_patch(DjangoTyPlugin.adjust_call_signature(&CallRequest {
        context: semantic_context("library.models"),
        callee: TypeExpr::expression("django.db.models.manager.Manager.from_queryset"),
        receiver: Some(receiver.clone()),
        arguments: Vec::new(),
        existing_signature: None,
        default_return_type: None,
        project_index: None,
    }));

    assert_eq!(patch.signature.parameters.len(), 2);
    assert_eq!(
        patch.signature.parameters[0]
            .type_expr
            .as_ref()
            .unwrap()
            .expression,
        "type[django.db.models.query.QuerySet[typing.Any, typing.Any]]"
    );
    assert!(patch.signature.parameters[0].required);
    assert!(!patch.signature.parameters[1].required);
    assert_eq!(patch.signature.return_type, receiver.type_expr);

    assert!(matches!(
        DjangoTyPlugin.adjust_call_signature(&CallRequest {
            context: semantic_context("library.models"),
            callee: TypeExpr::expression("library.models.build_manager"),
            receiver: None,
            arguments: Vec::new(),
            existing_signature: None,
            default_return_type: None,
            project_index: None,
        }),
        PluginResponse::NoChange
    ));
}

#[test]
fn packaged_manifest_uses_the_wheel_artifact() {
    let manifest = django_ty::packaged_manifest();

    assert_eq!(manifest.id, "django-ty");
    assert_eq!(manifest.version, env!("CARGO_PKG_VERSION"));
    assert_eq!(manifest.ty_compatibility.requirement, ">=0.59.0,<0.60.0");
    assert!(matches!(
        manifest.runtime,
        ty_plugin_sdk::protocol::RuntimeSpec::Wasm(ref wasm) if wasm.artifact == "django_ty.wasm"
    ));
    assert!(manifest.capabilities.class_transform);
    assert!(manifest.capabilities.call_return);
    assert!(manifest.capabilities.project_index);
}

#[test]
fn project_index_collects_models_settings_fields_virtual_types_and_reverse_relations() {
    let response = build_index(vec![
        book_model(),
        author_model(),
        tag_model(),
        user_model(),
    ]);
    let PluginResponse::ProjectIndex(index) = response else {
        panic!("expected project index");
    };

    assert!(index.diagnostics.is_empty());
    assert_eq!(
        index.plugin_index["settings"]["django.conf.settings.AUTH_USER_MODEL"],
        "accounts.User"
    );
    assert_eq!(index.plugin_index["models"][BOOK]["fields"]["title"], "str");
    assert_eq!(
        index.plugin_index["models"][BOOK]["fields"]["pages"],
        "int | None"
    );
    assert_eq!(
        index.plugin_index["models"][BOOK]["fields"]["author"],
        AUTHOR
    );
    assert_eq!(
        index.plugin_index["models"][BOOK]["fields"]["owner"],
        format!("{USER} | None")
    );
    assert_eq!(
        index.plugin_index["models"][BOOK]["fields"]["author_id"],
        "int"
    );
    assert_eq!(
        index.plugin_index["models"][BOOK]["fields"]["owner_id"],
        "int | None"
    );
    assert!(
        index
            .virtual_types
            .iter()
            .any(|ty| ty.name == format!("django_ty.virtual.{BOOK}.Manager"))
    );
    assert!(index.virtual_types.iter().any(|ty| {
        ty.name == format!("django_ty.virtual.{BOOK}.ValuesRow")
            && matches!(&ty.shape, VirtualTypeShape::TypedDict { fields, .. } if fields.iter().any(|field| field.name == "title"))
    }));
    assert!(index.contributions.iter().any(|contribution| {
        contribution.conflict_key == format!("{AUTHOR}.books")
            && matches!(&contribution.patch, ContributionPatch::Field(field) if field.name == "books")
    }));
    assert!(index.contributions.iter().any(|contribution| {
        contribution.conflict_key == format!("{TAG}.book_set")
            && matches!(&contribution.patch, ContributionPatch::Field(field) if field.name == "book_set")
    }));
}

#[test]
fn project_index_inherits_models_tracks_query_names_and_contributes_choices() {
    const TIMESTAMPED: &str = "library.models.Timestamped";
    const ARTICLE: &str = "library.models.Article";
    const ARTICLE_PROXY: &str = "library.models.ArticleProxy";
    const REVIEW: &str = "library.models.Review";

    let timestamped = model_class(
        TIMESTAMPED,
        vec![scalar_field("created_at", "DateTimeField")],
    );
    let mut article = derived_model_class(
        ARTICLE,
        "Timestamped",
        vec![
            scalar_field("title", "CharField"),
            field(
                "status",
                "models.CharField",
                vec![keyword_value(
                    "choices",
                    LiteralValue::ClassRef(SymbolRef {
                        qualified_name: "Status".to_string(),
                    }),
                )],
            ),
        ],
    );
    article.nested_classes.push(NestedClassSummary {
        name: "Status".to_string(),
        qualified_name: format!("{ARTICLE}.Status"),
        bases: vec![TypeExpr::expression("django.db.models.TextChoices")],
        class_constants: Vec::new(),
        source: source("/project/models.py", 20),
    });
    let proxy = derived_model_class(ARTICLE_PROXY, ARTICLE, Vec::new());
    let review = model_class(
        REVIEW,
        vec![relation_field(
            "article",
            "ForeignKey",
            positional_class(ARTICLE),
            vec![keyword_str("related_query_name", "reviews")],
        )],
    );

    let PluginResponse::ProjectIndex(index) =
        build_index(vec![timestamped, article.clone(), proxy, review])
    else {
        panic!("expected project index");
    };

    for model in [ARTICLE, ARTICLE_PROXY] {
        assert_eq!(
            index.plugin_index["models"][model]["fields"]["created_at"],
            "datetime.datetime"
        );
        assert_eq!(
            index.plugin_index["models"][model]["field_types"]["created_at"],
            "django.db.models.DateTimeField[typing.Any, typing.Any]"
        );
    }
    assert_eq!(
        index.plugin_index["models"][ARTICLE]["query_fields"]["reviews"],
        REVIEW
    );
    assert!(index.contributions.iter().any(|contribution| {
        contribution.conflict_key == format!("{ARTICLE_PROXY}.created_at")
            && matches!(&contribution.patch, ContributionPatch::Field(field) if field.name == "created_at")
    }));
    assert!(index.contributions.iter().any(|contribution| {
        contribution.conflict_key == format!("{ARTICLE}.Status.label")
            && matches!(&contribution.patch, ContributionPatch::Member(member) if member.name == "label")
    }));

    let PluginResponse::ClassPatch(patch) = DjangoTyPlugin.analyze_class(&AnalyzeClassRequest {
        context: semantic_context("library.models"),
        class: article,
        project_index: Some(index.plugin_index),
    }) else {
        panic!("expected class patch");
    };
    assert!(patch.instance_members.iter().any(|member| {
        member.name == "get_status_display"
            && member.access.instance_get_type().expression == "typing.Callable[..., str]"
    }));
}

#[test]
fn project_index_reports_unknown_targets_and_reverse_conflicts() {
    let unknown = model_class(
        "library.models.Orphan",
        vec![relation_field(
            "missing",
            "ForeignKey",
            positional_str("missing.App"),
            Vec::new(),
        )],
    );
    let first = model_class(
        "library.models.First",
        vec![relation_field(
            "author",
            "ForeignKey",
            positional_class(AUTHOR),
            vec![keyword_str("related_name", "dupe")],
        )],
    );
    let second = model_class(
        "library.models.Second",
        vec![relation_field(
            "author",
            "ForeignKey",
            positional_class(AUTHOR),
            vec![keyword_str("related_name", "dupe")],
        )],
    );

    let PluginResponse::ProjectIndex(index) =
        build_index(vec![unknown, first, second, author_model()])
    else {
        panic!("expected project index");
    };

    assert!(
        index
            .diagnostics
            .iter()
            .any(|diagnostic| diagnostic.id == "django-ty.unknown-relation-target")
    );
    assert!(
        index
            .diagnostics
            .iter()
            .any(|diagnostic| diagnostic.id == "django-ty.reverse-relation-conflict")
    );
}

#[test]
fn class_transform_adds_fields_managers_relation_ids_and_optional_constructor_args() {
    let index = project_index(vec![
        book_model(),
        author_model(),
        tag_model(),
        user_model(),
    ]);
    let PluginResponse::ClassPatch(patch) = analyze_book(index) else {
        panic!("expected class patch");
    };

    assert!(patch.fields.iter().any(|field| field.name == "id"));
    assert!(patch.fields.iter().any(|field| field.name == "pk"));
    let title = patch
        .fields
        .iter()
        .find(|field| field.name == "title")
        .unwrap();
    assert_eq!(title.instance_get_type.expression, "str");
    assert!(
        title
            .constructor_parameter
            .as_ref()
            .is_some_and(|parameter| !parameter.required)
    );
    let owner = patch
        .fields
        .iter()
        .find(|field| field.name == "owner")
        .unwrap();
    assert_eq!(owner.instance_get_type.expression, format!("{USER} | None"));
    assert_eq!(
        owner.instance_set_type.as_ref().unwrap().expression,
        format!("{USER} | int | None")
    );
    assert!(
        patch
            .fields
            .iter()
            .any(|field| field.name == "author_id" && field.instance_get_type.expression == "int")
    );
    assert!(patch.fields.iter().any(
        |field| field.name == "owner_id" && field.instance_get_type.expression == "int | None"
    ));
    assert!(
        patch
            .class_members
            .iter()
            .any(|member| member.name == "objects")
    );
    assert!(
        patch
            .class_members
            .iter()
            .any(|member| member.name == "_default_manager")
    );
}

#[test]
fn non_models_and_non_manager_calls_do_not_change() {
    assert_eq!(
        DjangoTyPlugin.analyze_class(&AnalyzeClassRequest {
            context: semantic_context("plain"),
            class: non_model_class(),
            project_index: None,
        }),
        PluginResponse::NoChange
    );
    assert_eq!(
        DjangoTyPlugin.adjust_call_return(&CallRequest {
            context: semantic_context("plain"),
            callee: TypeExpr::expression("plain.function"),
            receiver: None,
            arguments: Vec::new(),
            existing_signature: None,
            default_return_type: None,
            project_index: None,
        }),
        PluginResponse::NoChange
    );
}

#[test]
fn manager_and_queryset_methods_return_model_queryset_rows_and_async_wrappers() {
    let index = project_index(vec![
        book_model(),
        author_model(),
        tag_model(),
        user_model(),
    ]);

    let filter = return_patch(call(
        "filter",
        manager_receiver(BOOK),
        vec![keyword_int("pages", 10)],
        index.clone(),
    ));
    assert_eq!(
        filter.return_type.expression,
        format!("django.db.models.query.QuerySet[{BOOK}, {BOOK}]")
    );
    assert!(filter.diagnostics.is_empty());

    let get = return_patch(call(
        "get",
        manager_receiver(BOOK),
        Vec::new(),
        index.clone(),
    ));
    assert_eq!(get.return_type.expression, BOOK);

    let qs_get = return_patch(call(
        "get",
        queryset_receiver(BOOK, "library.models.BookRow"),
        Vec::new(),
        index.clone(),
    ));
    assert_eq!(qs_get.return_type.expression, "library.models.BookRow");

    let first = return_patch(call(
        "first",
        manager_receiver(BOOK),
        Vec::new(),
        index.clone(),
    ));
    assert_eq!(first.return_type.expression, format!("{BOOK} | None"));

    let tuple = return_patch(call(
        "get_or_create",
        manager_receiver(BOOK),
        Vec::new(),
        index.clone(),
    ));
    assert_eq!(tuple.return_type.expression, format!("tuple[{BOOK}, bool]"));

    let count = return_patch(call(
        "count",
        manager_receiver(BOOK),
        Vec::new(),
        index.clone(),
    ));
    assert_eq!(count.return_type.expression, "int");

    let exists = return_patch(call(
        "exists",
        manager_receiver(BOOK),
        Vec::new(),
        index.clone(),
    ));
    assert_eq!(exists.return_type.expression, "bool");

    let latest = return_patch(call(
        "latest",
        manager_receiver(BOOK),
        Vec::new(),
        index.clone(),
    ));
    assert_eq!(latest.return_type.expression, BOOK);

    let async_get = return_patch(call(
        "aget",
        manager_receiver(BOOK),
        Vec::new(),
        index.clone(),
    ));
    assert_eq!(
        async_get.return_type.expression,
        format!("typing.Coroutine[object, object, {BOOK}]")
    );

    let async_create = return_patch(call(
        "acreate",
        manager_receiver(BOOK),
        Vec::new(),
        index.clone(),
    ));
    assert_eq!(
        async_create.return_type.expression,
        format!("typing.Coroutine[object, object, {BOOK}]")
    );

    let async_tuple = return_patch(call(
        "aget_or_create",
        manager_receiver(BOOK),
        Vec::new(),
        index.clone(),
    ));
    assert_eq!(
        async_tuple.return_type.expression,
        format!("typing.Coroutine[object, object, tuple[{BOOK}, bool]]")
    );

    let async_first = return_patch(call(
        "afirst",
        manager_receiver(BOOK),
        Vec::new(),
        index.clone(),
    ));
    assert_eq!(
        async_first.return_type.expression,
        format!("typing.Coroutine[object, object, {BOOK} | None]")
    );

    let async_count = return_patch(call(
        "acount",
        manager_receiver(BOOK),
        Vec::new(),
        index.clone(),
    ));
    assert_eq!(
        async_count.return_type.expression,
        "typing.Coroutine[object, object, int]"
    );

    let async_exists = return_patch(call("aexists", manager_receiver(BOOK), Vec::new(), index));
    assert_eq!(
        async_exists.return_type.expression,
        "typing.Coroutine[object, object, bool]"
    );
}

#[test]
fn values_values_list_and_annotate_compute_row_types() {
    let index = project_index(vec![
        book_model(),
        author_model(),
        tag_model(),
        user_model(),
    ]);

    let values = return_patch(call(
        "values",
        manager_receiver(BOOK),
        vec![positional_str("title"), positional_str("pages")],
        index.clone(),
    ));
    assert_eq!(
        values.return_type.expression,
        r#"django.db.models.query.QuerySet[library.models.Book, TypedDict({"title": str, "pages": int | None})]"#
    );

    let all_values = return_patch(call(
        "values",
        manager_receiver(BOOK),
        Vec::new(),
        index.clone(),
    ));
    assert_eq!(
        all_values.return_type.expression,
        format!("django.db.models.query.QuerySet[{BOOK}, django_ty.virtual.{BOOK}.ValuesRow]")
    );

    let values_list = return_patch(call(
        "values_list",
        manager_receiver(BOOK),
        vec![positional_str("title"), positional_str("pages")],
        index.clone(),
    ));
    assert_eq!(
        values_list.return_type.expression,
        format!("django.db.models.query.QuerySet[{BOOK}, tuple[str, int | None]]")
    );

    let all_values_list = return_patch(call(
        "values_list",
        manager_receiver(BOOK),
        Vec::new(),
        index.clone(),
    ));
    assert!(
        all_values_list
            .return_type
            .expression
            .starts_with(&format!("django.db.models.query.QuerySet[{BOOK}, tuple["))
    );

    let flat = return_patch(call(
        "values_list",
        manager_receiver(BOOK),
        vec![positional_str("title"), keyword_bool("flat", true)],
        index.clone(),
    ));
    assert_eq!(
        flat.return_type.expression,
        format!("django.db.models.query.QuerySet[{BOOK}, str]")
    );

    let named = return_patch(call(
        "values_list",
        manager_receiver(BOOK),
        vec![positional_str("title"), keyword_bool("named", true)],
        index.clone(),
    ));
    assert!(
        named
            .return_type
            .expression
            .contains(r#"NamedTuple("DjangoTyValuesListRow", {"title": str})"#)
    );

    let named_all = return_patch(call(
        "values_list",
        manager_receiver(BOOK),
        vec![keyword_bool("named", true)],
        index.clone(),
    ));
    assert_eq!(
        named_all.return_type.expression,
        format!("django.db.models.query.QuerySet[{BOOK}, django_ty.virtual.{BOOK}.ValuesListRow]")
    );

    let annotated = return_patch(call(
        "annotate",
        queryset_receiver(BOOK, BOOK),
        vec![keyword_value(
            "available",
            LiteralValue::Bool { value: true },
        )],
        index.clone(),
    ));
    assert!(
        annotated
            .return_type
            .expression
            .contains(r#"Class("DjangoTyAnnotatedRow", {"available": bool},"#)
    );

    let annotate_no_args = return_patch(call(
        "annotate",
        queryset_receiver(BOOK, BOOK),
        Vec::new(),
        index.clone(),
    ));
    assert_eq!(
        annotate_no_args.return_type.expression,
        format!("django.db.models.query.QuerySet[{BOOK}, {BOOK}]")
    );

    let annotate_literals = return_patch(call(
        "annotate",
        queryset_receiver(BOOK, BOOK),
        vec![
            keyword_value("score", LiteralValue::Int { value: 1 }),
            keyword_value(
                "label",
                LiteralValue::Str {
                    value: "x".to_string(),
                },
            ),
            keyword_value("maybe", LiteralValue::None),
            keyword_value("opaque", LiteralValue::Unknown),
        ],
        index,
    ));
    assert!(
        annotate_literals
            .return_type
            .expression
            .contains(r#""score": int"#)
    );
    assert!(
        annotate_literals
            .return_type
            .expression
            .contains(r#""label": str"#)
    );
    assert!(
        annotate_literals
            .return_type
            .expression
            .contains(r#""maybe": None"#)
    );
    assert!(
        annotate_literals
            .return_type
            .expression
            .contains(r#""opaque": object"#)
    );
}

#[test]
fn prefetch_create_bulk_save_and_metadata_hooks_are_specialized_and_validated() {
    let index = project_index(vec![
        book_model(),
        author_model(),
        tag_model(),
        user_model(),
    ]);

    let prefetch = return_patch(call(
        "prefetch_related",
        manager_receiver(BOOK),
        vec![ArgumentSummary {
            name: None,
            kind: ArgumentKind::Positional,
            type_expr: Some(TypeExpr::annotation(
                r#"Prefetch[Literal["tags"], QuerySet[Tag, Tag], Literal["loaded_tags"]]"#,
            )),
            value: LiteralValue::Unknown,
            source: Some(source("/project/use.py", 12)),
        }],
        index.clone(),
    ));
    assert!(
        prefetch.return_type.expression.contains(
            r#"Class("DjangoTyPrefetchedRow", {"loaded_tags": list[library.models.Tag]}"#
        )
    );

    let bad_create = return_patch(call(
        "create",
        manager_receiver(BOOK),
        vec![keyword_value(
            "pages",
            LiteralValue::Str {
                value: "many".to_string(),
            },
        )],
        index.clone(),
    ));
    assert_eq!(
        bad_create.diagnostics[0].id,
        "django-ty.invalid-lookup-value"
    );

    let bad_defaults = return_patch(call(
        "update_or_create",
        manager_receiver(BOOK),
        vec![ArgumentSummary {
            name: Some("defaults".to_string()),
            kind: ArgumentKind::Keyword,
            type_expr: Some(TypeExpr::annotation("dict[str, str]")),
            value: LiteralValue::Dict {
                entries: vec![LiteralDictEntry {
                    key: LiteralValue::Str {
                        value: "pages".to_string(),
                    },
                    value: LiteralValue::Unknown,
                }],
            },
            source: Some(source("/project/use.py", 13)),
        }],
        index.clone(),
    ));
    assert_eq!(
        bad_defaults.diagnostics[0].id,
        "django-ty.invalid-lookup-value"
    );

    let bad_ordering = return_patch(call(
        "order_by",
        manager_receiver(BOOK),
        vec![positional_str("-missing")],
        index.clone(),
    ));
    assert_eq!(bad_ordering.diagnostics[0].id, "django-ty.unknown-lookup");

    let bad_bulk = return_patch(call(
        "bulk_update",
        manager_receiver(BOOK),
        vec![
            positional_list(Vec::new()),
            positional_list(vec![LiteralValue::Str {
                value: "missing".to_string(),
            }]),
        ],
        index.clone(),
    ));
    assert_eq!(bad_bulk.return_type.expression, "int");
    assert_eq!(bad_bulk.diagnostics[0].id, "django-ty.unknown-lookup");

    let save = return_patch(DjangoTyPlugin.adjust_call_return(&CallRequest {
        context: semantic_context("library.use"),
        callee: TypeExpr::expression(format!("{BOOK}.save")),
        receiver: Some(ReceiverSummary {
            type_expr: TypeExpr::annotation(BOOK),
            nominal_class: Some(BOOK.to_string()),
            generic_arguments: Vec::new(),
            plugin_metadata: json!({}),
        }),
        arguments: vec![keyword_list(
            "update_fields",
            vec![LiteralValue::Str {
                value: "missing".to_string(),
            }],
        )],
        existing_signature: None,
        default_return_type: Some(TypeExpr::annotation("None")),
        project_index: Some(index.clone()),
    }));
    assert_eq!(save.return_type.expression, "None");
    assert_eq!(save.diagnostics[0].id, "django-ty.unknown-lookup");

    let options_receiver = ReceiverSummary {
        type_expr: TypeExpr::annotation(format!("django.db.models.options.Options[{BOOK}]")),
        nominal_class: Some("django.db.models.options.Options".to_string()),
        generic_arguments: vec![TypeExpr::annotation(BOOK)],
        plugin_metadata: json!({}),
    };
    let get_field = |name: &str| {
        DjangoTyPlugin.adjust_call_return(&CallRequest {
            context: semantic_context("library.use"),
            callee: TypeExpr::expression("django.db.models.options.Options.get_field"),
            receiver: Some(options_receiver.clone()),
            arguments: vec![positional_str(name)],
            existing_signature: None,
            default_return_type: None,
            project_index: Some(index.clone()),
        })
    };
    assert_eq!(
        return_patch(get_field("title")).return_type.expression,
        "django.db.models.CharField[typing.Any, typing.Any]"
    );
    assert_eq!(
        return_patch(get_field("missing")).diagnostics[0].id,
        "django-ty.unknown-lookup"
    );
}

#[test]
fn lazy_strings_custom_managers_and_queryset_subclasses_take_their_specific_paths() {
    let lazy = return_patch(DjangoTyPlugin.adjust_call_return(&CallRequest {
        context: semantic_context("library.use"),
        callee: TypeExpr::expression("django.utils.translation.gettext_lazy"),
        receiver: None,
        arguments: vec![positional_str("hello")],
        existing_signature: None,
        default_return_type: None,
        project_index: None,
    }));
    assert_eq!(lazy.return_type.expression, "str");

    let custom = model_class(
        "library.models.CustomManaged",
        vec![
            field("objects", "LocalManager", Vec::new()),
            field("secondary", "django.db.models.Manager", Vec::new()),
        ],
    );
    let index = project_index(vec![custom.clone()]);
    let PluginResponse::ClassPatch(patch) = DjangoTyPlugin.analyze_class(&AnalyzeClassRequest {
        context: semantic_context("library.models"),
        class: custom,
        project_index: Some(index.clone()),
    }) else {
        panic!("expected class patch");
    };
    assert!(patch.class_members.iter().any(|member| {
        member.name == "objects"
            && member.access.instance_get_type().expression == "library.models.LocalManager"
    }));
    assert!(patch.class_members.iter().any(|member| {
        member.name == "secondary"
            && member
                .access
                .instance_get_type()
                .expression
                .contains("django_ty.virtual.library.models.CustomManaged.Manager")
    }));

    let concrete_queryset = ReceiverSummary {
        type_expr: TypeExpr::annotation("library.querysets.PublishedQuerySet"),
        nominal_class: Some("library.querysets.PublishedQuerySet".to_string()),
        generic_arguments: vec![TypeExpr::annotation("library.models.CustomManaged")],
        plugin_metadata: json!({}),
    };
    assert_eq!(
        call("filter", concrete_queryset, Vec::new(), index.clone()),
        PluginResponse::NoChange
    );

    let virtual_queryset = ReceiverSummary {
        type_expr: TypeExpr::annotation("django_ty.virtual.library.models.CustomManaged.QuerySet"),
        nominal_class: Some("library.querysets.CustomQuerySet".to_string()),
        generic_arguments: vec![TypeExpr::annotation("library.models.CustomManaged")],
        plugin_metadata: json!({}),
    };
    assert!(matches!(
        call("filter", virtual_queryset, Vec::new(), index),
        PluginResponse::CallReturnPatch(_)
    ));
}

#[test]
fn lookup_validation_accepts_supported_shapes_and_reports_bad_values() {
    let index = project_index(vec![
        book_model(),
        author_model(),
        tag_model(),
        user_model(),
    ]);
    let ok = return_patch(call(
        "filter",
        manager_receiver(BOOK),
        vec![
            keyword_value(
                "title__icontains",
                LiteralValue::Str {
                    value: "rust".to_string(),
                },
            ),
            keyword_value(
                "pages__in",
                LiteralValue::List {
                    items: vec![
                        LiteralValue::Int { value: 1 },
                        LiteralValue::Int { value: 2 },
                    ],
                },
            ),
            keyword_value("pages__range", LiteralValue::Unknown),
            keyword_value("owner__isnull", LiteralValue::Bool { value: false }),
            keyword_value("owner", LiteralValue::None),
            keyword_value(
                "author",
                LiteralValue::ClassRef(SymbolRef {
                    qualified_name: AUTHOR.to_string(),
                }),
            ),
            keyword_value(
                "author__name__exact",
                LiteralValue::Str {
                    value: "Ada".to_string(),
                },
            ),
        ],
        index.clone(),
    ));
    assert!(ok.diagnostics.is_empty());

    let creation_defaults = return_patch(call(
        "update_or_create",
        manager_receiver(BOOK),
        vec![
            keyword_value(
                "title",
                LiteralValue::Str {
                    value: "rust".to_string(),
                },
            ),
            keyword_value(
                "defaults",
                LiteralValue::Dict {
                    entries: Vec::new(),
                },
            ),
            keyword_value(
                "create_defaults",
                LiteralValue::Dict {
                    entries: Vec::new(),
                },
            ),
        ],
        index.clone(),
    ));
    assert!(creation_defaults.diagnostics.is_empty());

    let bad = return_patch(call(
        "filter",
        manager_receiver(BOOK),
        vec![
            keyword_value(
                "pages__icontains",
                LiteralValue::Str {
                    value: "wrong".to_string(),
                },
            ),
            keyword_value("title__isnull", LiteralValue::Int { value: 1 }),
            keyword_value(
                "missing__exact",
                LiteralValue::Str {
                    value: "x".to_string(),
                },
            ),
            keyword_value(
                "pages__range",
                LiteralValue::List {
                    items: vec![LiteralValue::Int { value: 1 }],
                },
            ),
            keyword_value(
                "pages__in",
                LiteralValue::Dict {
                    entries: Vec::new(),
                },
            ),
            keyword_value("__bad", LiteralValue::Unknown),
        ],
        index,
    ));
    assert!(
        bad.diagnostics
            .iter()
            .any(|diagnostic| diagnostic.id == "django-ty.invalid-lookup-value")
    );
    assert!(
        bad.diagnostics
            .iter()
            .any(|diagnostic| diagnostic.id == "django-ty.unknown-lookup")
    );
}

#[test]
fn values_reports_unknown_field_names_and_invalid_flat_named_combo_no_changes() {
    let index = project_index(vec![
        book_model(),
        author_model(),
        tag_model(),
        user_model(),
    ]);

    let bad_values = return_patch(call(
        "values",
        manager_receiver(BOOK),
        vec![positional_str("missing")],
        index.clone(),
    ));
    assert_eq!(bad_values.diagnostics[0].id, "django-ty.unknown-lookup");

    let invalid_combo = call(
        "values_list",
        manager_receiver(BOOK),
        vec![keyword_bool("flat", true), keyword_bool("named", true)],
        index.clone(),
    );
    assert_eq!(invalid_combo, PluginResponse::NoChange);

    let invalid_flat_without_fields = call(
        "values_list",
        manager_receiver(BOOK),
        vec![keyword_bool("flat", true)],
        index.clone(),
    );
    assert_eq!(invalid_flat_without_fields, PluginResponse::NoChange);

    let non_string_field_arg = return_patch(call(
        "values",
        manager_receiver(BOOK),
        vec![ArgumentSummary {
            name: None,
            kind: ArgumentKind::Positional,
            type_expr: Some(TypeExpr::annotation("int")),
            value: LiteralValue::Int { value: 1 },
            source: Some(source("/project/use.py", 8)),
        }],
        index,
    ));
    assert!(non_string_field_arg.diagnostics.is_empty());
}

#[test]
fn one_to_one_related_name_plus_and_unknown_scalar_fields_are_handled() {
    let profile = model_class(
        "accounts.models.Profile",
        vec![
            relation_field(
                "user",
                "OneToOneField",
                positional_class(USER),
                vec![keyword_str("related_name", "+")],
            ),
            scalar_field("payload", "JSONField"),
            field("ignored", "django.db.models.UnknownField", Vec::new()),
        ],
    );
    let PluginResponse::ProjectIndex(index) = build_index(vec![profile.clone(), user_model()])
    else {
        panic!("expected project index");
    };
    assert!(
        !index
            .contributions
            .iter()
            .any(|contribution| contribution.conflict_key == "accounts.models.User.profile")
    );
    assert_eq!(
        index.plugin_index["models"]["accounts.models.Profile"]["fields"]["payload"],
        "object"
    );

    let PluginResponse::ClassPatch(patch) = DjangoTyPlugin.analyze_class(&AnalyzeClassRequest {
        context: semantic_context("accounts.models"),
        class: profile,
        project_index: Some(index.plugin_index),
    }) else {
        panic!("expected class patch");
    };
    assert!(patch.fields.iter().any(|field| field.name == "user_id"));
    assert!(!patch.fields.iter().any(|field| field.name == "ignored"));
}

#[test]
fn sdk_json_dispatch_round_trips_manifest_and_project_index() {
    let manifest_json = DjangoTyPlugin
        .handle_json(&ty_plugin_sdk::serde_json::to_string(&PluginRequest::Manifest).unwrap())
        .unwrap();
    let manifest_response: PluginResponse =
        ty_plugin_sdk::serde_json::from_str(&manifest_json).unwrap();
    assert!(matches!(manifest_response, PluginResponse::Manifest(_)));

    let request = PluginRequest::AdjustCallReturn(CallRequest {
        context: semantic_context("library.use"),
        callee: TypeExpr::expression("django.db.models.manager.Manager.exists"),
        receiver: Some(manager_receiver(BOOK)),
        arguments: Vec::new(),
        existing_signature: None,
        default_return_type: None,
        project_index: Some(project_index(vec![
            book_model(),
            author_model(),
            tag_model(),
            user_model(),
        ])),
    });
    let response_json = DjangoTyPlugin
        .handle_json(&ty_plugin_sdk::serde_json::to_string(&request).unwrap())
        .unwrap();
    let response: PluginResponse = ty_plugin_sdk::serde_json::from_str(&response_json).unwrap();
    assert!(matches!(response, PluginResponse::CallReturnPatch(_)));

    let request = BuildProjectIndexRequest {
        context: project_context(),
        classes: vec![book_model(), author_model(), tag_model(), user_model()],
        settings: settings(),
        assignments: Vec::new(),
        previous_index_fingerprint: Some("previous".to_string()),
    };
    let request_json = json!({
        "kind": "build-project-index",
        "context": request.context,
        "classes": request.classes,
        "settings": request.settings,
        "previous-index-fingerprint": request.previous_index_fingerprint,
    });
    let response_json = DjangoTyPlugin
        .handle_json(&ty_plugin_sdk::serde_json::to_string(&request_json).unwrap())
        .unwrap();
    let response: PluginResponse = ty_plugin_sdk::serde_json::from_str(&response_json).unwrap();
    assert!(matches!(response, PluginResponse::ProjectIndex(_)));
}

#[test]
fn relation_contribution_descriptor_shape_is_read_only_for_one_to_one() {
    let profile = model_class(
        "accounts.models.Profile",
        vec![relation_field(
            "user",
            "OneToOneField",
            positional_class(USER),
            vec![keyword_str("related_name", "profile")],
        )],
    );
    let PluginResponse::ProjectIndex(index) = build_index(vec![profile, user_model()]) else {
        panic!("expected project index");
    };
    let contribution = index
        .contributions
        .iter()
        .find(|contribution| contribution.conflict_key == format!("{USER}.profile"))
        .unwrap();
    let ContributionPatch::Field(field) = &contribution.patch else {
        panic!("expected field contribution");
    };
    assert_eq!(field.name, "profile");
    let Some(MemberAccessPatch::Descriptor {
        instance_get_type,
        instance_set_type,
        ..
    }) = &field.descriptor
    else {
        panic!("expected descriptor");
    };
    assert_eq!(instance_get_type.expression, "accounts.models.Profile");
    assert!(instance_set_type.is_none());
}

#[test]
fn relation_targets_support_to_keyword_self_and_unresolved_enum_fallbacks() {
    let node = model_class(
        "tree.models.Node",
        vec![
            field(
                "parent",
                "django.db.models.ForeignKey",
                vec![
                    ArgumentSummary {
                        name: Some("to".to_string()),
                        kind: ArgumentKind::Keyword,
                        type_expr: Some(TypeExpr::annotation("tree.models.Node")),
                        value: LiteralValue::Str {
                            value: "self".to_string(),
                        },
                        source: None,
                    },
                    positional_str("django.db.models.CASCADE"),
                ],
            ),
            field(
                "raw",
                "django.db.models.ForeignKey",
                vec![
                    ArgumentSummary {
                        name: None,
                        kind: ArgumentKind::Positional,
                        type_expr: Some(TypeExpr::annotation("external.models.Raw")),
                        value: LiteralValue::EnumRef(SymbolRef {
                            qualified_name: "external.models.Raw".to_string(),
                        }),
                        source: None,
                    },
                    positional_str("django.db.models.CASCADE"),
                ],
            ),
            field("missing_target", "django.db.models.ForeignKey", Vec::new()),
        ],
    );
    let PluginResponse::ProjectIndex(index) = build_index(vec![node]) else {
        panic!("expected project index");
    };
    assert_eq!(
        index.plugin_index["models"]["tree.models.Node"]["fields"]["parent"],
        "tree.models.Node"
    );
    assert!(
        index
            .diagnostics
            .iter()
            .any(|diagnostic| diagnostic.message.contains("external.models.Raw"))
    );
}

#[test]
fn manager_receiver_variants_and_missing_project_index_take_safe_paths() {
    let index = project_index(vec![
        book_model(),
        author_model(),
        tag_model(),
        user_model(),
    ]);
    let custom_receiver = ReceiverSummary {
        type_expr: TypeExpr::annotation(format!("library.models.BookManager[{BOOK}]")),
        nominal_class: Some("library.models.BookManager".to_string()),
        generic_arguments: vec![TypeExpr::annotation(BOOK)],
        plugin_metadata: json!({}),
    };
    let custom = return_patch(call("filter", custom_receiver, Vec::new(), index.clone()));
    assert_eq!(
        custom.return_type.expression,
        format!("django.db.models.query.QuerySet[{BOOK}, {BOOK}]")
    );

    let virtual_receiver = ReceiverSummary {
        type_expr: TypeExpr::annotation(format!("django_ty.virtual.{BOOK}.Manager")),
        nominal_class: Some(format!("django_ty.virtual.{BOOK}.Manager")),
        generic_arguments: vec![TypeExpr::annotation(BOOK)],
        plugin_metadata: json!({}),
    };
    let virtual_result = return_patch(call("exists", virtual_receiver, Vec::new(), index));
    assert_eq!(virtual_result.return_type.expression, "bool");

    let no_index = return_patch(DjangoTyPlugin.adjust_call_return(&CallRequest {
        context: semantic_context("library.use"),
        callee: TypeExpr::expression("django.db.models.manager.Manager.filter"),
        receiver: Some(manager_receiver(BOOK)),
        arguments: vec![keyword_int("missing", 1)],
        existing_signature: None,
        default_return_type: None,
        project_index: None,
    }));
    assert!(no_index.diagnostics.is_empty());

    let not_manager = DjangoTyPlugin.adjust_call_return(&CallRequest {
        context: semantic_context("library.use"),
        callee: TypeExpr::expression("plain.Plain.filter"),
        receiver: Some(ReceiverSummary {
            type_expr: TypeExpr::annotation("plain.Plain"),
            nominal_class: Some("plain.Plain".to_string()),
            generic_arguments: vec![TypeExpr::annotation(BOOK)],
            plugin_metadata: json!({}),
        }),
        arguments: Vec::new(),
        existing_signature: None,
        default_return_type: None,
        project_index: None,
    });
    assert_eq!(not_manager, PluginResponse::NoChange);

    let unknown_method = DjangoTyPlugin.adjust_call_return(&CallRequest {
        context: semantic_context("library.use"),
        callee: TypeExpr::expression("django.db.models.manager.Manager.unhandled"),
        receiver: Some(manager_receiver(BOOK)),
        arguments: Vec::new(),
        existing_signature: None,
        default_return_type: None,
        project_index: Some(json!({ "models": {} })),
    });
    assert_eq!(unknown_method, PluginResponse::NoChange);
}

#[test]
fn project_index_builds_custom_queryset_managers_and_typed_settings_contributions() {
    let self_parameter = Parameter {
        name: Some("self".to_string()),
        kind: ParameterKind::PositionalOrKeyword,
        type_expr: None,
        required: true,
    };
    let flag_parameter = Parameter {
        name: Some("flag".to_string()),
        kind: ParameterKind::PositionalOrKeyword,
        type_expr: Some(TypeExpr::annotation("bool")),
        required: true,
    };
    let queryset = ClassSummary {
        qualified_name: "library.models.BookQuerySet".to_string(),
        bases: vec![TypeExpr::annotation(
            "django.db.models.query.QuerySet[library.models.Book, library.models.Book]",
        )],
        decorators: Vec::new(),
        metaclass: None,
        fields: Vec::new(),
        methods: Vec::new(),
        nested_classes: Vec::new(),
        class_constants: Vec::new(),
        source: SymbolSource::default(),
    };
    let specialized_queryset = ClassSummary {
        qualified_name: "library.models.SpecialBookQuerySet".to_string(),
        bases: vec![TypeExpr::annotation("BookQuerySet")],
        decorators: Vec::new(),
        metaclass: None,
        fields: Vec::new(),
        methods: vec![
            MethodSummary {
                name: "active".to_string(),
                decorators: Vec::new(),
                parameters: vec![self_parameter.clone(), flag_parameter],
                return_type: Some(
                    TypeExpr::annotation("Self")
                        .with_snapshot(TypeSnapshot::SelfType { bound: None }),
                ),
                is_public: true,
                source: SymbolSource::default(),
            },
            MethodSummary {
                name: "counted".to_string(),
                decorators: Vec::new(),
                parameters: vec![self_parameter.clone()],
                return_type: Some(TypeExpr::annotation("int")),
                is_public: true,
                source: SymbolSource::default(),
            },
            MethodSummary {
                name: "untyped".to_string(),
                decorators: Vec::new(),
                parameters: vec![self_parameter.clone()],
                return_type: None,
                is_public: true,
                source: SymbolSource::default(),
            },
            MethodSummary {
                name: "_private".to_string(),
                decorators: Vec::new(),
                parameters: vec![self_parameter],
                return_type: Some(TypeExpr::annotation("str")),
                is_public: false,
                source: SymbolSource::default(),
            },
        ],
        nested_classes: Vec::new(),
        class_constants: Vec::new(),
        source: SymbolSource::default(),
    };
    let manager_field = |name: &str, callee: &str, receiver: Option<&str>| FieldSummary {
        name: name.to_string(),
        annotation: None,
        assigned_value: Some(AssignedValueSummary::Call(CallValueSummary {
            callee: SymbolRef {
                qualified_name: callee.to_string(),
            },
            receiver: receiver.map(|qualified_name| ValueSummary {
                symbol: Some(SymbolRef {
                    qualified_name: qualified_name.to_string(),
                }),
                type_expr: None,
            }),
            arguments: Vec::new(),
            return_type: None,
        })),
        inferred_type: None,
        has_default: false,
        source: SymbolSource::default(),
    };
    let book = model_class(
        BOOK,
        vec![manager_field(
            "objects",
            "library.models.SpecialBookQuerySet.as_manager",
            Some("library.models.SpecialBookQuerySet"),
        )],
    );
    let article = model_class(
        "library.models.Article",
        vec![manager_field("objects", "BookManager", None)],
    );
    let magazine = model_class(
        "library.models.Magazine",
        vec![
            manager_field("objects", "library.models.BookManager", None),
            manager_field("external", "external.CustomManager", None),
        ],
    );
    let assignment_call =
        |qualified_name: &str, callee: &str, arguments: Vec<ArgumentSummary>| AssignmentSummary {
            name: qualified_name.rsplit('.').next().unwrap().to_string(),
            qualified_name: qualified_name.to_string(),
            assigned_value: AssignedValueSummary::Call(CallValueSummary {
                callee: SymbolRef {
                    qualified_name: callee.to_string(),
                },
                receiver: None,
                arguments,
                return_type: None,
            }),
            inferred_type: None,
            source: SymbolSource::default(),
        };
    let assignments = vec![
        AssignmentSummary {
            name: "literal".to_string(),
            qualified_name: "library.models.literal".to_string(),
            assigned_value: AssignedValueSummary::Literal {
                value: LiteralValue::Int { value: 1 },
            },
            inferred_type: None,
            source: SymbolSource::default(),
        },
        assignment_call("library.models.Other", "build_manager", Vec::new()),
        assignment_call(
            "library.models.NoArgumentManager",
            "django.db.models.Manager.from_queryset",
            Vec::new(),
        ),
        assignment_call(
            "library.models.InvalidManager",
            "django.db.models.Manager.from_queryset",
            vec![positional_str("not-a-class")],
        ),
        assignment_call(
            "library.models.MissingManager",
            "django.db.models.Manager.from_queryset",
            vec![positional_class("MissingQuerySet")],
        ),
        assignment_call(
            "library.models.BookManager",
            "django.db.models.Manager.from_queryset",
            vec![positional_class("SpecialBookQuerySet")],
        ),
    ];
    let setting_values = vec![
        ("FEATURE_ENABLED", LiteralValue::Bool { value: true }),
        ("MAX_RETRIES", LiteralValue::Int { value: 3 }),
        (
            "SITE_NAME",
            LiteralValue::Str {
                value: "Library".to_string(),
            },
        ),
        ("OPTIONAL_VALUE", LiteralValue::None),
        ("PAIR", LiteralValue::Tuple { items: Vec::new() }),
        ("ITEMS", LiteralValue::List { items: Vec::new() }),
        (
            "MAPPING",
            LiteralValue::Dict {
                entries: Vec::new(),
            },
        ),
        (
            "DYNAMIC_ENUM",
            LiteralValue::EnumRef(SymbolRef {
                qualified_name: "example.VALUE".to_string(),
            }),
        ),
        (
            "DYNAMIC_SYMBOL",
            LiteralValue::SymbolRef(SymbolRef {
                qualified_name: "example.value".to_string(),
            }),
        ),
        (
            "DYNAMIC_CLASS",
            LiteralValue::ClassRef(SymbolRef {
                qualified_name: "example.Type".to_string(),
            }),
        ),
        ("DYNAMIC_UNKNOWN", LiteralValue::Unknown),
        (
            "AUTH_USER_MODEL",
            LiteralValue::Str {
                value: "accounts.User".to_string(),
            },
        ),
    ]
    .into_iter()
    .map(|(name, value)| SettingValueSummary {
        name: name.to_string(),
        value,
        source: SymbolSource::default(),
    })
    .collect();
    let nested_user = model_class("project.accounts.models.User", Vec::new());
    let response = DjangoTyPlugin.build_project_index(&BuildProjectIndexRequest {
        context: project_context(),
        classes: vec![
            queryset,
            specialized_queryset,
            book,
            article,
            magazine,
            nested_user,
        ],
        settings: vec![SettingsModuleSummary {
            module: "project.settings".to_string(),
            values: setting_values,
            dependencies: Vec::new(),
            diagnostics: Vec::new(),
            source: SymbolSource::default(),
        }],
        assignments,
        previous_index_fingerprint: None,
    });
    let PluginResponse::ProjectIndex(index) = response else {
        panic!("expected project index");
    };

    assert_eq!(
        index.plugin_index["auth_user_model"],
        "project.accounts.models.User"
    );
    for model in [BOOK, "library.models.Article", "library.models.Magazine"] {
        assert_eq!(
            index.plugin_index["models"][model]["manager_queryset"],
            "library.models.SpecialBookQuerySet"
        );
    }
    let manager = index
        .virtual_types
        .iter()
        .find(|virtual_type| virtual_type.name == "django_ty.virtual.library.models.Book.Manager")
        .expect("custom manager virtual type");
    let VirtualTypeShape::Class { members, .. } = &manager.shape else {
        panic!("manager should be a class virtual type");
    };
    assert_eq!(
        members
            .iter()
            .map(|member| member.name.as_str())
            .collect::<Vec<_>>(),
        ["active", "counted", "untyped"]
    );
    let MemberAccessPatch::Callable { signature, .. } = &members[0].access else {
        panic!("queryset method should become a callable manager member");
    };
    assert_eq!(signature.parameters.len(), 1);
    assert_eq!(
        signature.return_type.expression,
        "library.models.SpecialBookQuerySet"
    );
    assert!(index.contributions.iter().any(|contribution| {
        contribution.conflict_key == "django.http.request.HttpRequest.user"
    }));
    assert_eq!(
        index
            .contributions
            .iter()
            .filter(|contribution| {
                contribution
                    .conflict_key
                    .starts_with("django.conf.LazySettings.")
            })
            .count(),
        8
    );
}

#[test]
fn auth_self_and_mutation_hooks_cover_success_and_safe_fallbacks() {
    let auth_request = |project_index| CallRequest {
        context: semantic_context("library.use"),
        callee: TypeExpr::expression("django.contrib.auth.get_user_model"),
        receiver: None,
        arguments: Vec::new(),
        existing_signature: None,
        default_return_type: None,
        project_index,
    };
    assert_eq!(
        DjangoTyPlugin.adjust_call_return(&auth_request(None)),
        PluginResponse::NoChange
    );
    let auth_return = return_patch(DjangoTyPlugin.adjust_call_return(&auth_request(Some(json!({
        "auth_user_model": USER
    })))));
    assert_eq!(auth_return.return_type.expression, format!("type[{USER}]"));

    let self_receiver = ReceiverSummary {
        type_expr: TypeExpr::annotation("Self").with_snapshot(TypeSnapshot::SelfType {
            bound: Some(Box::new(TypeSnapshot::expression(&TypeExpr::annotation(
                "library.models.BookQuerySet",
            )))),
        }),
        nominal_class: Some("library.models.BookQuerySet".to_string()),
        generic_arguments: vec![TypeExpr::annotation(BOOK), TypeExpr::annotation(BOOK)],
        plugin_metadata: json!({}),
    };
    let self_return = return_patch(DjangoTyPlugin.adjust_call_return(&CallRequest {
        context: semantic_context("library.use"),
        callee: TypeExpr::expression("library.models.BookQuerySet.filter"),
        receiver: Some(self_receiver),
        arguments: Vec::new(),
        existing_signature: None,
        default_return_type: None,
        project_index: Some(json!({ "models": { BOOK: { "fields": {} } } })),
    }));
    assert!(matches!(
        self_return.return_type.snapshot.as_deref(),
        Some(TypeSnapshot::SelfType { .. })
    ));
    let bulk_return = return_patch(call(
        "bulk_create",
        manager_receiver(BOOK),
        Vec::new(),
        json!({ "models": { BOOK: { "fields": {} } } }),
    ));
    assert_eq!(bulk_return.return_type.expression, format!("list[{BOOK}]"));

    let mutation = |operation| MutationRequest {
        context: semantic_context("library.use"),
        operation,
        receiver: TypeExpr::annotation("django.http.request._ImmutableQueryDict"),
        key: Some(positional_str("name")),
        value: Some(positional_str("Ada")),
        source: source("/project/use.py", 12),
        project_index: None,
    };
    assert_eq!(
        DjangoTyPlugin.validate_mutation(&mutation(MutationOperation::ItemDelete)),
        PluginResponse::NoChange
    );
    let PluginResponse::MutationDiagnostics(response) =
        DjangoTyPlugin.validate_mutation(&mutation(MutationOperation::ItemSet))
    else {
        panic!("expected mutation diagnostic");
    };
    assert_eq!(response.diagnostics.len(), 1);
    assert_eq!(
        response.diagnostics[0].id,
        "django-ty.immutable-querydict-write"
    );
    assert!(response.diagnostics[0].location.is_some());
}
