from optype.infer import infer


def yields_bool_and_int():
    yield True
    yield 1


def yields_exception_subclass_and_superclass():
    yield FileNotFoundError()
    yield OSError()


def yields_int_and_float():
    yield 1
    yield 1.0


def adds_int_literal_and_float(x):
    return x + 1, x + 1.0


def test_generator_yield_union_absorbs_bool_into_int():
    assert infer(yields_bool_and_int) == "() -> Generator[int]"


def test_union_absorbs_runtime_subclass_into_superclass():
    assert infer(yields_exception_subclass_and_superclass) == "() -> Generator[OSError]"


def test_generator_yield_union_does_not_use_numeric_tower_promotion():
    assert infer(yields_int_and_float) == "() -> Generator[int | float]"


def test_protocol_argument_union_keeps_int_literal_distinct_from_float():
    assert infer(adds_int_literal_and_float) == (
        "[R](x: CanAdd[Literal[1] | float, R]) -> tuple[R, R]"
    )
