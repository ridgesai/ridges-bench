#!/bin/bash
set -euo pipefail
cd /app
mkdir -p regression_tests
cat > regression_tests/test_meter_formatting.py <<'PY'
"""Reference regression suite for tqdm's static formatting helpers."""
import pytest

from tqdm import tqdm

format_sizeof = tqdm.format_sizeof
format_interval = tqdm.format_interval
format_num = tqdm.format_num
format_meter = tqdm.format_meter

FULL = "█"


@pytest.mark.parametrize("num, expected", [
    (1, "1.00"), (9.99, "9.99"), (9.996, "10.0"), (10, "10.0"), (99.94, "99.9"),
    (99.96, "100"), (999, "999"), (999.4, "999"), (999.6, "1.00k"), (1000, "1.00k"),
    (12345, "12.3k"), (1e6, "1.00M"), (2.5e9, "2.50G"), (1e24, "1.0Y"), (-1500, "-1.50k"),
])
def test_format_sizeof(num, expected):
    assert format_sizeof(num) == expected


def test_format_sizeof_suffix_and_divisor():
    assert format_sizeof(1000, suffix="B") == "1.00kB"
    assert format_sizeof(1024, divisor=1024) == "1.00k"
    assert format_sizeof(1000, divisor=1024) == "0.98k"
    assert format_sizeof(1536, "B", 1024) == "1.50kB"
    assert format_sizeof(3 * 1024 ** 3, "B", 1024) == "3.00GB"


@pytest.mark.parametrize("seconds, expected", [
    (0, "00:00"), (5, "00:05"), (59.9, "00:59"), (60, "01:00"), (61, "01:01"),
    (3599, "59:59"), (3600, "1:00:00"), (3661, "1:01:01"), (2 * 86400 + 5, "48:00:05"),
    (-65, "-01:05"),
])
def test_format_interval(seconds, expected):
    assert format_interval(seconds) == expected


@pytest.mark.parametrize("n, expected", [
    (0, "0"), (12, "12"), (123, "123"), (1234, "1234"), (123456, "123456"),
    (1e6, "1e+6"), (1234567, "1234567"), (0.5, "0.5"), (0.00001, "1e-5"),
    (123.456, "123"), (1.0, "1"),
])
def test_format_num(n, expected):
    assert format_num(n) == expected


def test_meter_default_layout():
    assert format_meter(0, 100, 0) == "  0%|          | 0/100 [00:00<?, ?it/s]"
    assert format_meter(20, 100, 10) == " 20%|" + FULL * 2 + " " * 8 + "| 20/100 [00:10<00:40,  2.00it/s]"
    assert format_meter(100, 100, 50) == "100%|" + FULL * 10 + "| 100/100 [00:50<00:00,  2.00it/s]"
    assert format_meter(3, 12, 7200) == " 25%|" + FULL * 2 + "▌" + " " * 7 + "| 3/12 [2:00:00<6:00:00, 2400.00s/it]"


def test_meter_ascii():
    assert format_meter(50, 100, 25, ascii=True) == " 50%|#####     | 50/100 [00:25<00:25,  2.00it/s]"
    assert format_meter(5, 10, 1, ascii="-=") == " 50%|=====-----| 5/10 [00:01<00:01,  5.00it/s]"


def test_meter_ncols():
    out = format_meter(20, 100, 10, ncols=40)
    assert out == " 20%|▍ | 20/100 [00:10<00:40,  2.00it/s]"
    assert len(out) == 40
    assert format_meter(20, 100, 10, ncols=0) == " 20% 20/100 [00:10<00:40,  2.00it/s]"


def test_meter_prefix():
    expected = "Load:  20%|" + FULL * 2 + " " * 8 + "| 20/100 [00:10<00:40,  2.00it/s]"
    assert format_meter(20, 100, 10, prefix="Load") == expected
    assert format_meter(20, 100, 10, prefix="Load: ") == expected


def test_meter_unknown_total():
    assert format_meter(20, None, 10) == "20it [00:10,  2.00it/s]"
    assert format_meter(20, None, 10, prefix="x") == "x: 20it [00:10,  2.00it/s]"
    assert format_meter(150, 100, 10) == "150it [00:10, 15.00it/s]"


def test_meter_unit():
    assert format_meter(20, 100, 10, unit="B").endswith("| 20/100 [00:10<00:40,  2.00B/s]")


def test_meter_unit_scale_true():
    out = format_meter(2000, 10000, 1, unit_scale=True, unit="B")
    assert out == " 20%|" + FULL * 2 + " " * 8 + "| 2.00k/10.0k [00:01<00:04, 2.00kB/s]"


def test_meter_unit_divisor():
    out = format_meter(2048, 10240, 1, unit_scale=True, unit_divisor=1024, unit="B")
    assert out.endswith("| 2.00k/10.0k [00:01<00:04, 2.05kB/s]")
    # unit_divisor is ignored without unit_scale
    assert format_meter(2048, 10240, 1, unit_divisor=1024).endswith("| 2048/10240 [00:01<00:04, 2048.00it/s]")


def test_meter_numeric_unit_scale():
    out = format_meter(20, 100, 10, unit_scale=10)
    assert out.endswith("| 200/1000 [00:10<00:40, 20.00it/s]")


def test_meter_rate_and_inverse_rate():
    assert format_meter(20, 100, 40).endswith("| 20/100 [00:40<02:40,  2.00s/it]")
    assert format_meter(1, 100, 10).endswith("| 1/100 [00:10<16:30, 10.00s/it]")
    assert format_meter(10, 100, 10).endswith("| 10/100 [00:10<01:30,  1.00it/s]")
    assert format_meter(20, 100, 10, rate=4).endswith("| 20/100 [00:10<00:20,  4.00it/s]")


def test_meter_initial():
    assert format_meter(20, 100, 10, initial=5).endswith("| 20/100 [00:10<00:53,  1.50it/s]")


def test_meter_postfix():
    out = format_meter(20, 100, 10, postfix="loss=0.1")
    assert out.endswith("| 20/100 [00:10<00:40,  2.00it/s, loss=0.1]")


def test_meter_bar_format_fields():
    fmt = "{n}/{total} {percentage:.0f}% {remaining} {rate_fmt}"
    assert format_meter(20, 100, 10, bar_format=fmt) == "20/100 20% 00:40  2.00it/s"
    fmt = "{rate_noinv_fmt} {rate_inv_fmt} {elapsed_s} {remaining_s}"
    assert format_meter(20, 100, 10, bar_format=fmt) == " 2.00it/s  0.50s/it 10 40.0"
    fmt = "{remaining}|{rate_fmt}|{elapsed}"
    assert format_meter(0, 100, 0, bar_format=fmt) == "?|?it/s|00:00"


def test_meter_bar_format_empty_desc_drops_colon():
    assert format_meter(20, 100, 10, bar_format="{desc}: {n_fmt}") == "20"
    assert format_meter(20, 100, 10, prefix="d", bar_format="{desc}: {n_fmt}") == "d: 20"


def test_meter_bar_format_bar_width_and_type():
    assert format_meter(20, 100, 10, bar_format="[{bar}]", ncols=12) == "[" + FULL * 2 + " " * 8 + "]"
    out = format_meter(20, 100, 10, bar_format="{l_bar}{bar:5}{r_bar}", ascii=True)
    assert out == " 20%|#    | 20/100 [00:10<00:40,  2.00it/s]"
    assert format_meter(20, 100, 10, bar_format="{bar:10a}") == "##        "
    out = format_meter(20, 100, 10, bar_format="{bar:-5}", ncols=20, ascii=True)
    assert out == "###            "


def test_meter_bar_format_unknown_total():
    assert format_meter(20, None, 10, bar_format="{n_fmt}|{bar}|", ncols=20) == "20|" + " " * 16 + "|"
PY
# Stage the new files so the oracle control sees them in git diff HEAD (runs inside the task container).
git add -A regression_tests
