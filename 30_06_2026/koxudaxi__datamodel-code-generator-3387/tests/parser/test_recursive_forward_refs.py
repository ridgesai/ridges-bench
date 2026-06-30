from __future__ import annotations

import ast
import importlib
import json
from typing import Any

from datamodel_code_generator.parser.base import ParseConfig, Parser

MODEL_NAME = "ISA95PropertyDataType"
FIELD_NAME = "children"


def recursive_schema() -> dict[str, Any]:
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "definitions": {
            MODEL_NAME: {
                "title": MODEL_NAME,
                "type": "object",
                "properties": {
                    FIELD_NAME: {
                        "type": "array",
                        "items": {"$ref": f"#/definitions/{MODEL_NAME}"},
                    }
                },
            }
        },
        "$ref": f"#/definitions/{MODEL_NAME}",
    }


def make_json_schema_parser() -> Parser:
    parser_module = importlib.import_module("datamodel_code_generator.parser.jsonschema")
    parser_class = getattr(parser_module, "JsonSchemaParser")
    parser = parser_class(
        json.dumps(recursive_schema()),
        target_python_version="3.10",
        use_standard_collections=True,
        use_union_operator=True,
    )
    assert isinstance(parser, Parser)
    return parser


def generate_recursive_model(*, disable_future_imports: bool) -> str:
    parser = make_json_schema_parser()
    generated = Parser.parse(
        parser,
        with_import=True,
        format_=False,
        disable_future_imports=disable_future_imports,
    )
    assert isinstance(generated, str)
    return generated


def field_annotation(code: str, class_name: str, field_name: str) -> ast.AST:
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for item in node.body:
            if (
                isinstance(item, ast.AnnAssign)
                and isinstance(item.target, ast.Name)
                and item.target.id == field_name
            ):
                return item.annotation
    raise AssertionError(f"field {field_name!r} was not generated on {class_name!r}")


def annotation_contains_name(annotation: ast.AST, name: str) -> bool:
    return any(isinstance(node, ast.Name) and node.id == name for node in ast.walk(annotation))


def annotation_contains_safe_self_reference(annotation: ast.AST, class_name: str) -> bool:
    return any(
        (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value == class_name
        )
        or (isinstance(node, ast.Name) and node.id == "Self")
        or (isinstance(node, ast.Attribute) and node.attr == "Self")
        for node in ast.walk(annotation)
    )


def self_reference_f821_candidates(code: str, class_name: str) -> set[str]:
    tree = ast.parse(code)
    candidates: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for item in node.body:
            annotation = getattr(item, "annotation", None)
            if annotation is not None and annotation_contains_name(annotation, class_name):
                candidates.add(class_name)
    return candidates


def execute_generated_code(code: str) -> dict[str, Any]:
    namespace: dict[str, Any] = {}
    exec(code, namespace)
    return namespace


def test_non_deferred_recursive_field_uses_forward_reference_safe_annotation():
    generated = generate_recursive_model(disable_future_imports=True)

    annotation = field_annotation(generated, MODEL_NAME, FIELD_NAME)

    assert not annotation_contains_name(annotation, MODEL_NAME)
    assert annotation_contains_safe_self_reference(annotation, MODEL_NAME)

    namespace = execute_generated_code(generated)
    model = namespace[MODEL_NAME]
    instance = model(children=[])
    assert instance.children == []


def test_non_deferred_recursive_field_has_no_self_reference_f821_candidate():
    generated = generate_recursive_model(disable_future_imports=True)

    assert self_reference_f821_candidates(generated, MODEL_NAME) == set()


def test_deferred_annotations_keep_existing_bare_recursive_annotation_style():
    generated = generate_recursive_model(disable_future_imports=False)

    annotation = field_annotation(generated, MODEL_NAME, FIELD_NAME)

    assert annotation_contains_name(annotation, MODEL_NAME)
    namespace = execute_generated_code(generated)
    assert MODEL_NAME in namespace


def test_parse_config_represents_non_deferred_annotation_generation():
    config = ParseConfig(
        with_import=True,
        use_deferred_annotations=False,
        code_formatter=None,
        module_split_mode=None,
        all_exports_scope=None,
        all_exports_collision_strategy=None,
    )

    assert config.with_import is True
    assert config.use_deferred_annotations is False
