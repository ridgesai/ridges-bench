import ast
import json

from datamodel_code_generator.parser.jsonschema import JsonSchemaParser


CONST_ENUM_VALUES = ["Frontend", "Server-side"]


def _parser(schema=None):
    return JsonSchemaParser(json.dumps(schema or {}))


def _schema_object(parser, schema):
    schema_type = parser.SCHEMA_OBJECT_TYPE
    if hasattr(schema_type, "model_validate"):
        return schema_type.model_validate(schema)
    return schema_type.parse_obj(schema)


def _const_enum_schema(keyword):
    return {
        "type": "string",
        keyword: [{"const": value} for value in CONST_ENUM_VALUES],
    }


def _default_value(field):
    if not isinstance(field.default, str):
        return field.default
    try:
        return ast.literal_eval(field.default)
    except (SyntaxError, ValueError):
        return field.default


def _referenced_model(data_type):
    assert data_type.reference is not None
    model = data_type.reference.source
    assert model is not None
    return model


def _wrapped_reference_field(model):
    fields = getattr(model, "fields", [])
    if len(fields) != 1:
        return None
    field = fields[0]
    if getattr(field, "data_type", None) is None:
        return None
    if field.data_type.reference is None:
        return None
    return field


def _enum_model_from_data_type(data_type):
    model = _referenced_model(data_type)
    wrapped_field = _wrapped_reference_field(model)
    if wrapped_field is not None:
        return _referenced_model(wrapped_field.data_type)
    return model


def _enum_values_from_model(model):
    return [_default_value(field) for field in model.fields]


def _enum_values_from_data_type(data_type):
    return _enum_values_from_model(_enum_model_from_data_type(data_type))


def _assert_enum_values(data_type, expected_values):
    assert _enum_values_from_data_type(data_type) == expected_values


def _literal_values(data_type):
    values = list(data_type.literals)
    for nested_data_type in data_type.data_types:
        values.extend(_literal_values(nested_data_type))
    return values


def _find_field(parser, public_name):
    for model in parser.results:
        for field in getattr(model, "fields", []):
            names = {
                getattr(field, "name", None),
                getattr(field, "alias", None),
                getattr(field, "original_name", None),
            }
            if public_name in names:
                return field
    raise AssertionError(f"field {public_name!r} was not generated")


def test_parse_raw_parses_property_one_of_const_values_as_enum_model():
    parser = _parser(
        {
            "title": "Issue",
            "type": "object",
            "properties": {
                "technologyArea": _const_enum_schema("oneOf"),
            },
            "required": ["technologyArea"],
        }
    )

    parser.parse_raw()

    field = _find_field(parser, "technologyArea")
    _assert_enum_values(field.data_type, CONST_ENUM_VALUES)


def test_parse_item_parses_one_of_const_alternatives_as_enum_values():
    parser = _parser()
    item = _schema_object(parser, _const_enum_schema("oneOf"))

    data_type = parser.parse_item(
        "TechnologyArea",
        item,
        ["#", "properties", "technologyArea"],
    )

    _assert_enum_values(data_type, CONST_ENUM_VALUES)


def test_parse_root_type_parses_root_one_of_const_alternatives_as_enum_values():
    parser = _parser()
    item = _schema_object(parser, _const_enum_schema("oneOf"))

    data_type = parser.parse_root_type("TechnologyArea", item, ["#"])

    _assert_enum_values(data_type, CONST_ENUM_VALUES)


def test_parse_item_handles_any_of_const_alternatives_like_one_of():
    parser = _parser()
    item = _schema_object(parser, _const_enum_schema("anyOf"))

    data_type = parser.parse_item(
        "TechnologyArea",
        item,
        ["#", "properties", "technologyArea"],
    )

    _assert_enum_values(data_type, CONST_ENUM_VALUES)


def test_nullable_combined_const_enum_keeps_nullable_enum_wrapper():
    parser = _parser()
    item = _schema_object(
        parser,
        {
            "oneOf": [
                {"const": 1},
                {"const": 2},
                {"type": "null"},
            ]
        },
    )

    data_type = parser.parse_item("Status", item, ["#", "properties", "status"])

    model = _referenced_model(data_type)
    nullable_field = _wrapped_reference_field(model)
    assert nullable_field is not None
    assert nullable_field.nullable is True
    _assert_enum_values(nullable_field.data_type, [1, 2])


def test_parse_enum_exposes_enum_member_values():
    parser = _parser()
    item = _schema_object(
        parser,
        {
            "type": "string",
            "enum": CONST_ENUM_VALUES,
        },
    )

    data_type = parser.parse_enum(
        "TechnologyArea",
        item,
        ["#", "definitions", "TechnologyArea"],
    )

    _assert_enum_values(data_type, CONST_ENUM_VALUES)


def test_parse_enum_as_literal_exposes_literal_values_and_nullability():
    parser = _parser()
    item = _schema_object(
        parser,
        {
            "type": "string",
            "enum": [*CONST_ENUM_VALUES, None],
        },
    )

    data_type = parser.parse_enum_as_literal(item)

    assert _literal_values(data_type) == CONST_ENUM_VALUES
    assert data_type.is_optional is True
