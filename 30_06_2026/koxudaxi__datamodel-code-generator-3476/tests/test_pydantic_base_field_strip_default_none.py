from datamodel_code_generator.model.pydantic_base import DataModelField
from datamodel_code_generator.types import DataType


def make_field(*, is_optional=False, default=None):
    return DataModelField(
        data_type=DataType(type="str", is_optional=is_optional),
        default=default,
        extras={"description": "generated metadata"},
        strip_default_none=True,
    )


def test_non_optional_none_default_is_omitted_when_metadata_is_present():
    field = make_field()

    assert field.field == "Field(description='generated metadata')"


def test_optional_none_default_is_preserved_when_metadata_is_present():
    field = make_field(is_optional=True)

    assert field.field == "Field(None, description='generated metadata')"


def test_explicit_non_none_default_is_preserved_when_strip_default_none_is_enabled():
    field = make_field(default="fallback")

    assert field.field == "Field('fallback', description='generated metadata')"
