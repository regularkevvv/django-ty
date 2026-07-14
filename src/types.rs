use ty_plugin_sdk::protocol::{
    ImportBinding, MemberPatch, TypeExpr, TypeSnapshot, VirtualTypeField,
};

pub fn annotation(expression: impl Into<String>) -> TypeExpr {
    let mut expression = expression.into();
    let mut imports = Vec::new();
    for (qualified_name, alias) in [
        ("datetime.datetime", "__django_ty_datetime"),
        ("datetime.timedelta", "__django_ty_timedelta"),
        ("datetime.date", "__django_ty_date"),
        ("datetime.time", "__django_ty_time"),
        ("decimal.Decimal", "__django_ty_decimal"),
        ("uuid.UUID", "__django_ty_uuid"),
    ] {
        if !expression.contains(qualified_name) {
            continue;
        }
        let (module, name) = qualified_name
            .rsplit_once('.')
            .expect("qualified imports contain a module");
        expression = expression.replace(qualified_name, alias);
        imports.push(ImportBinding {
            module: module.to_string(),
            name: name.to_string(),
            alias: Some(alias.to_string()),
        });
    }
    let mut ty = TypeExpr::annotation(expression);
    ty.imports = imports;
    ty
}

pub fn canonical_type_expression(ty: &TypeExpr) -> String {
    let mut expression = ty.expression.clone();
    for binding in &ty.imports {
        let Some(alias) = binding.alias.as_deref() else {
            continue;
        };
        expression = expression.replace(alias, &format!("{}.{}", binding.module, binding.name));
    }
    expression
}

pub fn expression(expression: impl Into<String>) -> TypeExpr {
    TypeExpr::expression(expression)
}

pub fn nullable(expression: impl Into<String>, is_nullable: bool) -> TypeExpr {
    let expression = expression.into();
    if is_nullable {
        annotation(format!("{expression} | None"))
    } else {
        annotation(expression)
    }
}

pub fn queryset_type(model_type: &TypeExpr, row_type: &TypeExpr) -> TypeExpr {
    let mut ty = annotation(format!(
        "django.db.models.query.QuerySet[{}, {}]",
        model_type.expression, row_type.expression
    ));
    ty.imports.extend(model_type.imports.clone());
    ty.imports.extend(row_type.imports.clone());
    ty.imports.sort_by(|left, right| {
        (&left.module, &left.name, &left.alias).cmp(&(&right.module, &right.name, &right.alias))
    });
    ty.imports.dedup();
    ty.snapshot = Some(Box::new(TypeSnapshot::Nominal {
        qualified_name: "django.db.models.query.QuerySet".to_string(),
        arguments: vec![type_snapshot(model_type), type_snapshot(row_type)],
    }));
    ty
}

pub fn type_snapshot(ty: &TypeExpr) -> TypeSnapshot {
    ty.snapshot
        .as_deref()
        .cloned()
        .unwrap_or_else(|| TypeSnapshot::expression(ty))
}

pub fn manager_virtual_type_name(model_name: &str) -> String {
    format!("django_ty.virtual.{model_name}.Manager")
}

pub fn queryset_virtual_type_name(model_name: &str) -> String {
    format!("django_ty.virtual.{model_name}.QuerySet")
}

pub fn values_row_virtual_type_name(model_name: &str) -> String {
    format!("django_ty.virtual.{model_name}.ValuesRow")
}

pub fn values_list_row_virtual_type_name(model_name: &str) -> String {
    format!("django_ty.virtual.{model_name}.ValuesListRow")
}

pub fn class_module_name(qualified_name: &str) -> &str {
    qualified_name
        .rsplit_once('.')
        .map_or("", |(module, _)| module)
}

pub fn class_short_name(qualified_name: &str) -> &str {
    qualified_name.rsplit('.').next().unwrap_or(qualified_name)
}

pub fn lower_model_name(qualified_name: &str) -> String {
    class_short_name(qualified_name).to_ascii_lowercase()
}

pub fn virtual_field(name: String, expression: String) -> VirtualTypeField {
    VirtualTypeField {
        name,
        type_expr: annotation(expression),
        required: true,
        read_only: false,
    }
}

pub fn member(name: impl Into<String>, ty: TypeExpr) -> MemberPatch {
    ty_plugin_sdk::dsl::replace_existing_member(ty_plugin_sdk::dsl::member(name, ty))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn portable_annotations_round_trip_qualified_standard_library_types() {
        let ty = annotation(
            "tuple[datetime.datetime, datetime.timedelta, datetime.date, datetime.time, decimal.Decimal, uuid.UUID]",
        );
        assert_eq!(ty.imports.len(), 6);
        assert!(ty.expression.contains("__django_ty_datetime"));
        assert_eq!(
            canonical_type_expression(&ty),
            "tuple[datetime.datetime, datetime.timedelta, datetime.date, datetime.time, decimal.Decimal, uuid.UUID]"
        );

        let mut without_alias = TypeExpr::annotation("Alias");
        without_alias.imports.push(ImportBinding {
            module: "example".to_string(),
            name: "Thing".to_string(),
            alias: None,
        });
        assert_eq!(canonical_type_expression(&without_alias), "Alias");
    }

    #[test]
    fn queryset_types_merge_and_deduplicate_imports() {
        let model = annotation("datetime.datetime");
        let row = annotation("tuple[datetime.datetime, decimal.Decimal]");
        let queryset = queryset_type(&model, &row);

        assert_eq!(queryset.imports.len(), 2);
        assert!(
            queryset
                .imports
                .windows(2)
                .all(|pair| pair[0].module <= pair[1].module)
        );
        let Some(TypeSnapshot::Nominal {
            qualified_name,
            arguments,
        }) = queryset.snapshot.as_deref()
        else {
            panic!("queryset type should carry a structural snapshot");
        };
        assert_eq!(qualified_name, "django.db.models.query.QuerySet");
        assert_eq!(arguments.len(), 2);
    }
}
