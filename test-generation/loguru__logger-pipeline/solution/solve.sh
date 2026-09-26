#!/bin/bash
set -euo pipefail
cd /app
mkdir -p regression_tests
cat > regression_tests/test_logger_pipeline.py <<'PY'
"""Reference regression suite for loguru's logger pipeline."""
import io
import itertools

import pytest

from loguru import logger

_counter = itertools.count()


def unique(prefix):
    return "%s_%d" % (prefix, next(_counter))


@pytest.fixture(autouse=True)
def isolated_logger():
    logger.remove()
    yield
    logger.remove()


class Sink:
    """Callable sink collecting messages (formatted strings with a .record)."""

    def __init__(self):
        self.messages = []

    def __call__(self, message):
        self.messages.append(message)

    @property
    def texts(self):
        return [str(m) for m in self.messages]

    @property
    def records(self):
        return [m.record for m in self.messages]


def add(fmt="{message}", **kwargs):
    sink = Sink()
    kwargs.setdefault("colorize", False)
    handler_id = logger.add(sink, format=fmt, **kwargs)
    return sink, handler_id


# --- add / remove -------------------------------------------------------------


def test_add_returns_increasing_ids_and_remove_stops_output():
    s1, i1 = add()
    s2, i2 = add()
    assert isinstance(i1, int) and isinstance(i2, int)
    assert i2 > i1
    logger.info("both")
    logger.remove(i1)
    logger.info("second only")
    logger.remove(i2)
    logger.info("nobody")
    assert s1.texts == ["both\n"]
    assert s2.texts == ["both\n", "second only\n"]


def test_ids_are_not_reused_after_remove():
    _, i1 = add()
    logger.remove(i1)
    _, i2 = add()
    assert i2 != i1


def test_remove_all_and_invalid_ids():
    s1, i1 = add()
    s2, _ = add()
    logger.remove()
    logger.info("gone")
    assert s1.texts == [] and s2.texts == []
    with pytest.raises(Exception):
        logger.remove(i1)
    with pytest.raises(Exception):
        logger.remove("0")


def test_stringio_sink():
    stream = io.StringIO()
    handler_id = logger.add(stream, format="{level} | {message}", colorize=False)
    logger.warning("careful")
    logger.info("fine")
    logger.remove(handler_id)
    assert stream.getvalue() == "WARNING | careful\nINFO | fine\n"


def test_invalid_sinks_and_arguments():
    with pytest.raises(Exception):
        logger.add(object())
    with pytest.raises(Exception):
        logger.add(Sink(), unknown_option=True)
    with pytest.raises(Exception):
        logger.add(Sink(), filter=3.5)
    with pytest.raises(Exception):
        logger.add(Sink(), format=12)
    with pytest.raises(Exception):
        logger.add(Sink(), level=1.5)
    with pytest.raises(Exception):
        logger.add(Sink(), level=-1)
    with pytest.raises(Exception):
        logger.add(Sink(), level="NOT_A_LEVEL")
    with pytest.raises(Exception):
        logger.add(Sink(), filter=filter)
    with pytest.raises(Exception):
        logger.add(Sink(), format=format)


def test_message_is_str_with_record():
    sink, _ = add("[{message}]")
    logger.info("hi")
    (msg,) = sink.messages
    assert isinstance(msg, str)
    assert msg == "[hi]\n"
    assert msg.record["message"] == "hi"
    assert msg.record["level"].name == "INFO"


# --- levels -------------------------------------------------------------------------


def test_level_threshold_by_name():
    sink, _ = add("{level.name}:{message}", level="WARNING")
    logger.debug("d")
    logger.info("i")
    logger.success("s")
    logger.warning("w")
    logger.error("e")
    logger.critical("c")
    assert sink.texts == ["WARNING:w\n", "ERROR:e\n", "CRITICAL:c\n"]


def test_level_threshold_by_number_is_inclusive():
    sink, _ = add("{level.no}", level=25)
    logger.info("i")
    logger.success("s")
    logger.log(24, "x")
    logger.log(25, "y")
    logger.log(26, "z")
    assert sink.texts == ["25\n", "25\n", "26\n"]


def test_default_level_is_debug():
    sink, _ = add("{level}")
    logger.trace("t")
    logger.debug("d")
    assert sink.texts == ["DEBUG\n"]


def test_trace_level_and_zero_threshold():
    sink, _ = add("{level.name} {level.no}", level=0)
    logger.trace("t")
    logger.log(0, "zero")
    assert sink.texts == ["TRACE 5\n", "Level 0 0\n"]


def test_builtin_levels():
    expected = {"TRACE": 5, "DEBUG": 10, "INFO": 20, "SUCCESS": 25, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
    for name, no in expected.items():
        lvl = logger.level(name)
        assert lvl.name == name
        assert lvl.no == no


def test_each_handler_has_its_own_threshold():
    low, _ = add(level="DEBUG")
    high, _ = add(level="ERROR")
    logger.debug("a")
    logger.error("b")
    assert low.texts == ["a\n", "b\n"]
    assert high.texts == ["b\n"]


def test_threshold_recomputed_after_remove():
    low, low_id = add(level="DEBUG")
    high, _ = add(level="ERROR")
    logger.remove(low_id)
    logger.debug("dropped")
    logger.error("kept")
    assert high.texts == ["kept\n"]
    low2, _ = add(level="TRACE")
    logger.trace("t")
    assert low2.texts == ["t\n"]


def test_log_with_integer_level():
    sink, _ = add("{level.name}|{level.no}|{message}")
    logger.log(33, "custom number")
    logger.log("INFO", "by name")
    assert sink.texts == ["Level 33|33|custom number\n", "INFO|20|by name\n"]
    with pytest.raises(Exception):
        logger.log("NOPE", "x")
    with pytest.raises(Exception):
        logger.log(2.5, "x")
    with pytest.raises(Exception):
        logger.log(-5, "x")


def test_custom_level_creation_and_use():
    name = unique("NOTICE")
    lvl = logger.level(name, no=27, icon="@", color="<red>")
    assert (lvl.name, lvl.no, lvl.icon) == (name, 27, "@")
    sink, _ = add("{level.name}/{level.no}/{level.icon}/{message}", level=26)
    logger.log(name, "hello {}", "you")
    assert sink.texts == ["%s/27/@/hello you\n" % name]
    assert logger.level(name) == lvl


def test_custom_level_filters_by_its_number():
    name = unique("QUIET")
    logger.level(name, no=15)
    sink, _ = add("{level}", level="INFO")
    logger.log(name, "hidden")
    assert sink.texts == []
    sink2, _ = add("{level}", level=name)
    logger.log(name, "shown")
    logger.debug("below")
    assert sink2.texts == [name + "\n"]


def test_update_existing_level_icon():
    name = unique("ICONIC")
    logger.level(name, no=22, icon="1")
    updated = logger.level(name, icon="2")
    assert (updated.no, updated.icon) == (22, "2")
    sink, _ = add("{level.icon}")
    logger.log(name, "x")
    assert sink.texts == ["2\n"]
    assert logger.level(name).icon == "2"


def test_level_errors():
    with pytest.raises(Exception):
        logger.level(unique("MISSING"))
    with pytest.raises(Exception):
        logger.level(unique("NONO"), icon="x")
    with pytest.raises(Exception):
        logger.level("INFO", no=21)
    with pytest.raises(Exception):
        logger.level(unique("BADNO"), no="3")
    with pytest.raises(Exception):
        logger.level(unique("NEG"), no=-1)
    with pytest.raises(Exception):
        logger.level(3)


def test_custom_level_defaults():
    name = unique("PLAIN")
    lvl = logger.level(name, no=12)
    assert (lvl.name, lvl.no, lvl.color, lvl.icon) == (name, 12, "", " ")
    sink, _ = add("[{level.icon}]{level}")
    logger.log(name, "x")
    assert sink.texts == ["[ ]%s\n" % name]


def test_level_zero_is_allowed():
    name = unique("ZERO")
    lvl = logger.level(name, no=0)
    assert lvl.no == 0


# --- format -----------------------------------------------------------------------------


def test_format_fields():
    sink, _ = add("{level}|{level.no}|{name}|{function}|{module}|{file.name}|{message}")
    logger.info("msg")
    (text,) = sink.texts
    assert text == "INFO|20|%s|test_format_fields|%s|%s.py|msg\n" % (__name__, __name__.rsplit(".", 1)[-1], __name__.rsplit(".", 1)[-1])


def test_format_extra_item():
    sink, _ = add("{extra[user]}:{message}")
    logger.bind(user="kim").info("x")
    assert sink.texts == ["kim:x\n"]


def test_format_spec_and_record_access():
    sink, _ = add("{level: <8}|{message:>5}|{extra}")
    logger.info("ab")
    assert sink.texts == ["INFO    |   ab|{}\n"]


def test_color_markup_is_stripped_without_colorize():
    sink, _ = add("<red>{level}</red> <b>{message}</b> <level>x</level>")
    logger.info("hello <green>tag</green>")
    assert sink.texts == ["INFO hello <green>tag</green> x\n"]


def test_extended_color_tags_are_stripped():
    fmt = "<fg 255>a</fg 255><bg 0>b</bg 0><fg #f0a>c</fg #f0a><fg 10,20,255>d</fg 10,20,255><fg red>e</fg red>{message}"
    sink, _ = add(fmt)
    logger.info("!")
    assert sink.texts == ["abcde!\n"]
    for bad in ["<fg 256>{message}</fg 256>", "<fg 1,2,256>{message}</fg 1,2,256>", "<fg #12>{message}</fg #12>"]:
        with pytest.raises(Exception):
            logger.add(Sink(), format=bad, colorize=False)


def test_escaped_markup_in_format():
    sink, _ = add("\\<red>{message}\\</red>")
    logger.info("m")
    assert sink.texts == ["<red>m</red>\n"]


def test_escaped_backslash_before_markup():
    sink, _ = add("\\\\<red>{message}</red>")
    logger.info("m")
    assert sink.texts == ["\\m\n"]


def test_invalid_markup_rejected():
    with pytest.raises(Exception):
        logger.add(Sink(), format="<red>{message}", colorize=False)
    with pytest.raises(Exception):
        logger.add(Sink(), format="{message}</red>", colorize=False)
    with pytest.raises(Exception):
        logger.add(Sink(), format="<red>{message}</blue>", colorize=False)


def test_callable_format():
    def fmt(record):
        return "{level.no}-{message}-" + record["extra"].get("tag", "none") + "\n"

    sink = Sink()
    logger.add(sink, format=fmt, colorize=False)
    logger.info("a")
    logger.bind(tag="t").warning("b")
    assert sink.texts == ["20-a-none\n", "30-b-t\n"]


def test_message_formatting_with_args_and_kwargs():
    sink, _ = add()
    logger.info("{} + {} = {total}", 1, 2, total=3)
    logger.info("literal {braces}")
    logger.info("{0}{0}", "x")
    assert sink.texts == ["1 + 2 = 3\n", "literal {braces}\n", "xx\n"]


def test_exception_in_format():
    sink, _ = add("{message}|{exception}")
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("boom")
    logger.info("plain")
    first, second = sink.texts
    assert first.startswith("boom|")
    assert "ZeroDivisionError" in first
    assert second == "plain|\n"
    assert sink.records[0]["exception"].type is ZeroDivisionError
    assert sink.records[1]["exception"] is None
    assert sink.records[0]["level"].name == "ERROR"


# --- filter -----------------------------------------------------------------------------


def test_filter_by_module_name_string():
    here = __name__
    top = here.split(".")[0]
    a, _ = add(filter=here)
    b, _ = add(filter=top)
    c, _ = add(filter=here + "_other")
    d, _ = add(filter=here[:-1])
    e, _ = add(filter=here + ".sub")
    logger.info("m")
    assert a.texts == ["m\n"]
    assert b.texts == ["m\n"]
    assert c.texts == []
    assert d.texts == []
    assert e.texts == []


def test_filter_empty_string_accepts_named_records():
    sink, _ = add(filter="")
    logger.info("m")
    assert sink.texts == ["m\n"]


def test_filter_callable():
    sink, _ = add(filter=lambda r: "keep" in r["extra"])
    logger.info("no")
    logger.bind(keep=1).info("yes")
    assert sink.texts == ["yes\n"]


def test_filter_dict_levels():
    here = __name__
    lower, _ = add(filter={here: "WARNING"})
    root_default, _ = add(filter={"": "ERROR"})
    disabled, _ = add(filter={here: False})
    enabled, _ = add(filter={"": False, here: True})
    numeric, _ = add(filter={here: 30})
    unrelated, _ = add(filter={"some.other.module": False})
    logger.info("i")
    logger.warning("w")
    logger.error("e")
    assert lower.texts == ["w\n", "e\n"]
    assert root_default.texts == ["e\n"]
    assert disabled.texts == []
    assert enabled.texts == ["i\n", "w\n", "e\n"]
    assert numeric.texts == ["w\n", "e\n"]
    assert unrelated.texts == ["i\n", "w\n", "e\n"]


def test_filter_dict_parent_module_rule():
    parent = __name__
    sink, _ = add(filter={parent + ".child": False, parent: "ERROR"})
    logger.warning("w")
    logger.error("e")
    assert sink.texts == ["e\n"]


def test_filter_dict_matches_whole_module_components():
    here = __name__
    partial, _ = add(filter={here[:-1]: False})
    longer, _ = add(filter={here + "x": False})
    child, _ = add(filter={here + ".child": False})
    logger.info("m")
    assert partial.texts == ["m\n"]
    assert longer.texts == ["m\n"]
    assert child.texts == ["m\n"]


def test_filter_dict_errors():
    with pytest.raises(Exception):
        logger.add(Sink(), filter={"a": "NOT_A_LEVEL"})
    with pytest.raises(Exception):
        logger.add(Sink(), filter={"a": 1.5})
    with pytest.raises(Exception):
        logger.add(Sink(), filter={1: "INFO"})
    with pytest.raises(Exception):
        logger.add(Sink(), filter={"a": -1})


def test_filter_and_level_combined():
    sink, _ = add(level="INFO", filter=lambda r: r["message"] != "skip")
    logger.debug("low")
    logger.info("skip")
    logger.info("ok")
    assert sink.texts == ["ok\n"]


# --- bind / contextualize / patch -------------------------------------------------------


def test_bind_returns_new_logger():
    sink, _ = add("{extra}")
    bound = logger.bind(a=1)
    rebound = bound.bind(b=2, a=3)
    logger.info("x")
    bound.info("x")
    rebound.info("x")
    assert [r["extra"] for r in sink.records] == [{}, {"a": 1}, {"a": 3, "b": 2}]


def test_contextualize():
    sink, _ = add("{extra}")
    with logger.contextualize(req="r1"):
        logger.info("a")
        with logger.contextualize(req="r2", user="u"):
            logger.info("b")
        logger.info("c")
    logger.info("d")
    assert [r["extra"] for r in sink.records] == [
        {"req": "r1"},
        {"req": "r2", "user": "u"},
        {"req": "r1"},
        {},
    ]


def test_bind_overrides_context():
    sink, _ = add("{extra[k]}")
    with logger.contextualize(k="ctx"):
        logger.info("a")
        logger.bind(k="bound").info("b")
    assert sink.texts == ["ctx\n", "bound\n"]


def test_contextualize_resets_after_error():
    sink, _ = add("{extra}")
    with pytest.raises(RuntimeError):
        with logger.contextualize(x=1):
            raise RuntimeError
    logger.info("after")
    assert sink.records[0]["extra"] == {}


def test_patch():
    sink, _ = add("{extra[p]}:{message}")

    def first(record):
        record["extra"]["p"] = 1

    def second(record):
        record["extra"]["p"] += 10
        record["message"] = record["message"].upper()

    patched = logger.patch(first).patch(second)
    patched.info("hi")
    logger.bind(p=0).info("plain")
    assert sink.texts == ["11:HI\n", "0:plain\n"]


def test_patch_runs_before_filter():
    sink, _ = add(filter=lambda r: r["extra"].get("ok"))
    logger.patch(lambda r: r["extra"].update(ok=True)).info("in")
    logger.info("out")
    assert sink.texts == ["in\n"]


# --- opt ------------------------------------------------------------------------------


def test_opt_lazy():
    sink, _ = add(level="INFO")
    calls = []

    def expensive():
        calls.append(1)
        return "value"

    logger.opt(lazy=True).debug("{}", expensive)
    assert calls == []
    logger.opt(lazy=True).info("{x}", x=expensive)
    assert calls == [1]
    assert sink.texts == ["value\n"]


def test_opt_record():
    sink, _ = add()
    logger.opt(record=True).info("{record[level].name} {record[function]}")
    logger.bind(a=1).opt(record=True).info("{record[extra][a]}")
    assert sink.texts == ["INFO test_opt_record\n", "1\n"]
    with pytest.raises(Exception):
        logger.opt(record=True).info("{}", record=1)


def test_opt_raw():
    sink, _ = add("[{level}] {message}")
    logger.opt(raw=True).info("raw text")
    logger.opt(raw=True).info("{}-{}", 1, 2)
    logger.info("normal")
    assert sink.texts == ["raw text", "1-2", "[INFO] normal\n"]


def test_opt_capture():
    sink, _ = add("{message} {extra}")
    logger.info("{a}", a=1)
    logger.opt(capture=False).info("{a}", a=2)
    assert sink.texts == ["1 {'a': 1}\n", "2 {}\n"]


def test_opt_depth():
    sink, _ = add("{function}")

    def wrapper():
        logger.opt(depth=1).info("x")
        logger.info("y")

    wrapper()
    assert sink.texts == ["test_opt_depth\n", "wrapper\n"]


def test_opt_exception():
    sink, _ = add("{message}\n{exception}")
    try:
        raise KeyError("k")
    except KeyError:
        logger.opt(exception=True).warning("with")
    err = ValueError("given")
    logger.opt(exception=err).info("instance")
    logger.opt(exception=False).info("without")
    assert "KeyError" in sink.texts[0]
    assert sink.records[0]["level"].name == "WARNING"
    assert sink.records[1]["exception"].value is err
    assert sink.texts[2] == "without\n\n"
    assert sink.records[2]["exception"] is None


def test_markup_in_messages_is_kept_verbatim():
    sink, _ = add()
    logger.info("<red>a</red>")
    logger.opt(lazy=True).info("<b>{}</b>", lambda: 1)
    logger.opt(capture=False).info("<i>")
    assert sink.texts == ["<red>a</red>\n", "<b>1</b>\n", "<i>\n"]


def test_opt_does_not_change_base_logger():
    sink, _ = add()
    logger.opt(raw=True)
    logger.info("x")
    assert sink.texts == ["x\n"]


def test_opt_keeps_bound_extra_and_patchers():
    sink, _ = add("{extra}")
    base = logger.bind(a=1).patch(lambda r: r["extra"].update(b=2))
    base.opt(lazy=True).info("x")
    assert sink.records[0]["extra"] == {"a": 1, "b": 2}


# --- catch ----------------------------------------------------------------------------


def test_catch_decorator_logs_and_returns_default():
    sink, _ = add("{level}|{message}")

    @logger.catch(default=-1)
    def div(a, b):
        return a / b

    assert div(4, 2) == 2
    assert div(1, 0) == -1
    assert len(sink.texts) == 1
    assert sink.texts[0].startswith("ERROR|")
    assert sink.records[0]["exception"].type is ZeroDivisionError


def test_catch_bare_decorator():
    sink, _ = add("{message}")

    @logger.catch
    def fail():
        raise ValueError

    assert fail() is None
    assert len(sink.records) == 1
    assert fail.__name__ == "fail"


def test_catch_context_manager_options():
    sink, _ = add("{level}|{message}", level=0)
    errors = []
    with logger.catch(level="WARNING", message="oops", onerror=errors.append):
        raise KeyError("x")
    assert sink.texts[0].startswith("WARNING|oops")
    assert isinstance(errors[0], KeyError)

    with pytest.raises(OSError):
        with logger.catch(reraise=True, message="again"):
            raise OSError
    assert sink.records[-1]["message"] == "again"

    with logger.catch(message="nothing"):
        pass
    assert len(sink.records) == 2


def test_catch_exception_type_and_exclude():
    sink, _ = add()
    with pytest.raises(ValueError):
        with logger.catch(KeyError):
            raise ValueError
    with pytest.raises(IndexError):
        with logger.catch(LookupError, exclude=IndexError):
            raise IndexError
    with logger.catch(LookupError, exclude=IndexError):
        raise KeyError
    assert len(sink.records) == 1
    assert sink.records[0]["exception"].type is KeyError


def test_catch_generator_and_class_error():
    sink, _ = add()

    @logger.catch(default="dflt")
    def gen():
        yield 1
        raise ValueError

    assert list(gen()) == [1]
    assert len(sink.records) == 1
    with pytest.raises(Exception):
        logger.catch(Exception)(type("K", (), {}))


def test_catch_uses_caller_record():
    sink, _ = add("{function}")

    @logger.catch
    def inner():
        raise ValueError

    inner()
    (record,) = sink.records
    assert record["function"] == "test_catch_uses_caller_record"
    assert record["exception"].type is ValueError
PY
# Stage the new files so the oracle control sees them in git diff HEAD.
git add -A regression_tests
