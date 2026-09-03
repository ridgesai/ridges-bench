#!/usr/bin/env python3
import ast
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


APP = Path("/app")
LOGS = Path("/logs/verifier")
ALLOWED = Path("netbox/ipam/querysets.py")
ORIGINAL = Path("/opt/task/original-querysets.py")
MANIFEST = Path("/opt/task/source-manifest.json")
HIDDEN_SOURCE = Path("/tests/vlangroup_utilization_hidden_test.py")
HIDDEN_TARGET = APP / "netbox/ipam/tests/ridges_vlangroup_utilization.py"
PIN = "00791344e68213bde942218283dce03cc3941c30"
AGENT_UID = 1000


class Report:
    def __init__(self):
        self.cases = []

    def check(self, name, function):
        try:
            detail = function()
            self.cases.append((name, True, detail))
            return detail
        except Exception as error:
            self.cases.append((name, False, f"{type(error).__name__}: {error}"))
            return None

    def write(self):
        suite = ET.Element(
            "testsuite",
            name="pg-netbox-vlangroup-utilization",
            tests=str(len(self.cases)),
            failures=str(sum(not passed for _, passed, _ in self.cases)),
            errors="0",
            skipped="0",
        )
        for name, passed, detail in self.cases:
            case = ET.SubElement(suite, "testcase", name=name)
            if not passed:
                failure = ET.SubElement(case, "failure", message=str(detail)[:1000])
                failure.text = str(detail)[:5000]
            output = ET.SubElement(case, "system-out")
            output.text = (
                json.dumps(detail, sort_keys=True)
                if isinstance(detail, (dict, list))
                else str(detail)
            )
        ET.ElementTree(suite).write(
            LOGS / "junit.xml", encoding="utf-8", xml_declaration=True
        )
        passed = all(result for _, result, _ in self.cases)
        (LOGS / "reward.txt").write_text("1\n" if passed else "0\n")
        return 0 if passed else 1


def run(command, timeout=420, check=True):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        command,
        cwd=APP,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    digest = hashlib.sha256("\0".join(command).encode()).hexdigest()[:12]
    (LOGS / f"command-{digest}.log").write_text(result.stdout)
    if check and result.returncode:
        raise AssertionError(
            f"command failed ({result.returncode}): {' '.join(command)}; "
            f"tail={result.stdout[-3500:]}"
        )
    return result


def file_record(path):
    mode = stat.S_IMODE(path.lstat().st_mode)
    if path.is_symlink():
        return {"kind": "symlink", "mode": mode, "target": path.readlink().as_posix()}
    if path.is_file():
        return {
            "kind": "file",
            "mode": mode,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    if path.is_dir():
        return {"kind": "directory", "mode": mode}
    return {"kind": "other", "mode": mode}


def source_identity():
    revision = Path("/opt/task/SOURCE_REVISION").read_text().strip()
    if revision != PIN:
        raise AssertionError("protected source revision changed")
    expected = json.loads(MANIFEST.read_text())
    actual = {}
    for path in sorted(APP.rglob("*")):
        relative = path.relative_to(APP)
        if relative == ALLOWED:
            continue
        actual[str(relative)] = file_record(path)
    if actual != expected:
        missing = sorted(set(expected) - set(actual))[:10]
        added = sorted(set(actual) - set(expected))[:10]
        changed = sorted(
            key for key in set(actual) & set(expected) if actual[key] != expected[key]
        )[:10]
        raise AssertionError(
            f"source drift: missing={missing}, added={added}, changed={changed}"
        )
    target = APP / ALLOWED
    if target.is_symlink() or not target.is_file():
        raise AssertionError("editable source is not a regular file")
    if target.stat().st_uid != AGENT_UID:
        raise AssertionError("editable source owner changed")
    return hashlib.sha256(target.read_bytes()).hexdigest()


def find_method(tree):
    matches = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "VLANGroupQuerySet":
            matches.extend(
                child
                for child in node.body
                if isinstance(child, ast.FunctionDef)
                and child.name == "annotate_utilization"
            )
    if len(matches) != 1:
        raise AssertionError(f"expected one target method, found {len(matches)}")
    return matches[0]


def bounded_method():
    original_text = ORIGINAL.read_text()
    candidate_text = (APP / ALLOWED).read_text()
    original = find_method(ast.parse(original_text))
    candidate = find_method(ast.parse(candidate_text))
    original_lines = original_text.splitlines(keepends=True)
    candidate_lines = candidate_text.splitlines(keepends=True)
    if original_lines[: original.lineno - 1] != candidate_lines[: candidate.lineno - 1]:
        raise AssertionError("source before target method changed")
    if original_lines[original.end_lineno :] != candidate_lines[candidate.end_lineno :]:
        raise AssertionError("source after target method changed")
    if type(original) is not type(candidate) or original._fields != candidate._fields:
        raise AssertionError("method header shape changed")

    def normalized_field(value):
        if isinstance(value, ast.AST):
            return ast.dump(value, include_attributes=False)
        if isinstance(value, list):
            return [normalized_field(item) for item in value]
        return value

    for field in original._fields:
        if field == "body":
            continue
        if normalized_field(getattr(original, field)) != normalized_field(
            getattr(candidate, field)
        ):
            raise AssertionError(f"method header field changed: {field}")
    if not candidate.body or ast.dump(
        candidate.body[0], include_attributes=False
    ) != ast.dump(original.body[0], include_attributes=False):
        raise AssertionError("local VLAN model import changed")
    body_text = "".join(candidate_lines[candidate.lineno - 1 : candidate.end_lineno])
    if len(body_text.encode()) > 5000:
        raise AssertionError("target method exceeds 5000 bytes")
    if len(list(ast.walk(candidate))) > 320:
        raise AssertionError("target method exceeds 320 AST nodes")

    forbidden_nodes = (
        ast.AsyncFunctionDef,
        ast.Await,
        ast.ClassDef,
        ast.Delete,
        ast.Global,
        ast.Import,
        ast.ImportFrom,
        ast.Lambda,
        ast.ListComp,
        ast.DictComp,
        ast.SetComp,
        ast.GeneratorExp,
        ast.Match,
        ast.Nonlocal,
        ast.Raise,
        ast.Try,
        ast.While,
        ast.With,
        ast.Yield,
        ast.YieldFrom,
    )
    dangerous_names = {
        "__import__",
        "breakpoint",
        "compile",
        "eval",
        "exec",
        "getattr",
        "globals",
        "locals",
        "open",
        "setattr",
        "vars",
    }
    dangerous_attributes = {
        "cursor",
        "execute",
        "executemany",
        "raw",
        "save",
        "update",
        "delete",
        "create",
        "bulk_create",
    }
    submitted_body = ast.Module(body=candidate.body[1:], type_ignores=[])
    for node in ast.walk(submitted_body):
        if isinstance(node, ast.FunctionDef) and node is not candidate:
            raise AssertionError("nested function definitions are forbidden")
        if isinstance(node, forbidden_nodes):
            raise AssertionError(f"forbidden construct: {type(node).__name__}")
        if isinstance(node, ast.Name) and (
            node.id in dangerous_names or "__" in node.id
        ):
            raise AssertionError(f"forbidden name: {node.id}")
        if isinstance(node, ast.Attribute) and (
            node.attr in dangerous_attributes or "__" in node.attr
        ):
            raise AssertionError(f"forbidden attribute: {node.attr}")
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and any(
                marker in node.value
                for marker in (
                    "Ridges VLAN",
                    "ridges-vlan",
                )
            )
        ):
            raise AssertionError("fixture-specific VLAN literal in production method")
    return {
        "candidate_sha256": hashlib.sha256(candidate_text.encode()).hexdigest(),
        "method_sha256": hashlib.sha256(body_text.encode()).hexdigest(),
    }


def parse_test_run(result, expected_count, required_names):
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    if result.returncode:
        raise AssertionError(
            f"test command failed ({result.returncode}); tail={plain[-4500:]}"
        )
    if not re.search(rf"Ran {expected_count} tests?", plain):
        raise AssertionError(f"expected exactly {expected_count} tests")
    if not re.search(r"^OK$", plain, re.MULTILINE):
        raise AssertionError("test run did not finish OK")
    for name in required_names:
        if name not in plain:
            raise AssertionError(f"required test not reported: {name}")
    return {
        "tests": expected_count,
        "stdout_sha256": hashlib.sha256(plain.encode()).hexdigest(),
    }


def focused_tests():
    labels = [
        "ipam.tests.test_api.VLANGroupTest.test_list_objects",
    ]
    result = run(
        [
            "python",
            "netbox/manage.py",
            "test",
            *labels,
            "--keepdb",
            "--noinput",
            "--verbosity",
            "2",
        ],
        timeout=600,
        check=False,
    )
    required = [
        "test_list_objects",
    ]
    return parse_test_run(result, 1, required)


def hidden_tests():
    if HIDDEN_TARGET.exists() or HIDDEN_TARGET.is_symlink():
        raise AssertionError("hidden test target already exists")
    shutil.copyfile(HIDDEN_SOURCE, HIDDEN_TARGET)
    os.chmod(HIDDEN_TARGET, 0o400)
    try:
        result = run(
            [
                "python",
                "netbox/manage.py",
                "test",
                "ipam.tests.ridges_vlangroup_utilization",
                "--keepdb",
                "--noinput",
                "--verbosity",
                "2",
            ],
            timeout=600,
            check=False,
        )
    finally:
        HIDDEN_TARGET.unlink(missing_ok=True)
    required = [
        "test_fractional_and_whole_utilization",
        "test_empty_and_custom_range_groups",
        "test_filtered_ordered_values_query_is_single_statement",
        "test_list_api_exposes_the_same_rounded_utilization",
    ]
    return parse_test_run(result, 4, required)


def role_identity():
    result = run(
        [
            "psql",
            "postgresql://solver:solver-development-35d886f2@postgres:5432/netbox_dev",
            "-At",
            "-c",
            "SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls "
            "FROM pg_roles WHERE rolname='solver'",
        ],
        timeout=30,
    )
    if result.stdout.strip() != "f|f|f|f|f":
        raise AssertionError(f"unexpected solver role: {result.stdout.strip()}")
    return result.stdout.strip()


def schema_identity():
    result = run(
        [
            "psql",
            "postgresql://solver:solver-development-35d886f2@postgres:5432/netbox_test",
            "-At",
            "-c",
            "SELECT n.nspname,c.relname,c.relkind FROM pg_class c "
            "JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname NOT IN ('pg_catalog','information_schema') "
            "ORDER BY 1,2,3",
        ],
        timeout=60,
    )
    return hashlib.sha256(result.stdout.encode()).hexdigest()


def main():
    LOGS.mkdir(parents=True, exist_ok=True)
    report = Report()
    report.check(
        "transported_patch_recorded",
        lambda: hashlib.sha256(
            Path("/logs/verifier/graded.patch").read_bytes()
        ).hexdigest(),
    )
    report.check("bounded_vlangroup_utilization_method", bounded_method)
    report.check("source_tree_conservation_before_tests", source_identity)
    report.check(
        "python_compilation",
        lambda: compile((APP / ALLOWED).read_text(), str(ALLOWED), "exec") or "ok",
    )
    report.check(
        "ruff_lint",
        lambda: (
            run(["ruff", "check", "--no-cache", str(ALLOWED)], timeout=120).returncode
        ),
    )
    report.check("postgres_solver_role_is_bounded", role_identity)
    report.check("focused_upstream_vlangroup_api_test", focused_tests)
    before = schema_identity()
    report.check("hidden_vlangroup_utilization_worlds", hidden_tests)
    report.check("source_tree_conservation_after_tests", source_identity)
    report.check(
        "database_schema_conservation",
        lambda: (
            before
            if schema_identity() == before
            else (_ for _ in ()).throw(AssertionError("database schema changed"))
        ),
    )
    return report.write()


if __name__ == "__main__":
    sys.exit(main())
