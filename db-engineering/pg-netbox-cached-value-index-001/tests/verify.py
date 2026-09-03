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
ALLOWED = Path("netbox/extras/migrations/0107_cachedvalue_extras_cachedvalue_object.py")
ORIGINAL = Path("/opt/task/original-cached-value-index.py")
MANIFEST = Path("/opt/task/source-manifest.json")
HIDDEN_SOURCE = Path("/tests/cached_value_index_hidden_test.py")
HIDDEN_TARGET = APP / "netbox/extras/tests/ridges_cached_value_index.py"
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
            name="pg-netbox-cached-value-index",
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
    if Path("/opt/task/SOURCE_REVISION").read_text().strip() != PIN:
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


def dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return dotted_name(node.value) + "." + node.attr
    raise AssertionError("unexpected callable in migration")


def keyword_map(call):
    if any(keyword.arg is None for keyword in call.keywords):
        raise AssertionError("expanded migration keywords are forbidden")
    return {keyword.arg: keyword.value for keyword in call.keywords}


def bounded_migration():
    original_text = ORIGINAL.read_text()
    candidate_text = (APP / ALLOWED).read_text()
    if len(candidate_text.encode()) > 1600:
        raise AssertionError("cached-value migration exceeds its bounded source budget")
    tree = ast.parse(candidate_text)
    if len(tree.body) != 2:
        raise AssertionError("migration module shape changed")
    expected_imports = ast.parse(original_text).body[:1]
    if ast.dump(ast.Module(body=tree.body[:1], type_ignores=[]), include_attributes=False) != ast.dump(
        ast.Module(body=expected_imports, type_ignores=[]), include_attributes=False
    ):
        raise AssertionError("migration imports changed")
    migration = tree.body[1]
    if not isinstance(migration, ast.ClassDef) or migration.name != "Migration":
        raise AssertionError("Migration class changed")
    if [dotted_name(base) for base in migration.bases] != ["migrations.Migration"]:
        raise AssertionError("Migration base changed")
    assignments = {
        node.targets[0].id: node.value
        for node in migration.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    }
    if set(assignments) != {"dependencies", "operations"}:
        raise AssertionError("migration class body changed")
    if ast.literal_eval(assignments["dependencies"]) != [
        ("extras", "0106_bookmark_user_cascade_deletion")
    ]:
        raise AssertionError("migration dependency changed")
    operations = assignments["operations"]
    if not isinstance(operations, (ast.List, ast.Tuple)) or len(operations.elts) != 1:
        raise AssertionError("expected exactly one migration operation")
    operation = operations.elts[0]
    if not isinstance(operation, ast.Call) or dotted_name(operation.func) != "migrations.AddIndex":
        raise AssertionError("expected one AddIndex operation")
    operation_keywords = keyword_map(operation)
    if set(operation_keywords) != {"model_name", "index"}:
        raise AssertionError("AddIndex contract changed")
    if ast.literal_eval(operation_keywords["model_name"]) != "cachedvalue":
        raise AssertionError("indexed model changed")
    index = operation_keywords["index"]
    if not isinstance(index, ast.Call) or dotted_name(index.func) != "models.Index":
        raise AssertionError("expected a Django Index")
    index_keywords = keyword_map(index)
    if set(index_keywords) != {"fields", "name"}:
        raise AssertionError("index contract changed")
    fields = list(ast.literal_eval(index_keywords["fields"]))
    if fields not in (["object_type"], ["object_type", "object_id"]):
        raise AssertionError(f"unexpected cached-value index fields: {fields}")
    if ast.literal_eval(index_keywords["name"]) != "extras_cachedvalue_object":
        raise AssertionError("cached-value index name changed")
    for node in ast.walk(tree):
        if isinstance(
            node,
            (
                ast.AsyncFunctionDef,
                ast.Await,
                ast.FunctionDef,
                ast.Global,
                ast.Import,
                ast.ImportFrom,
                ast.Lambda,
                ast.Nonlocal,
                ast.While,
                ast.With,
                ast.Yield,
                ast.YieldFrom,
            ),
        ):
            if node not in tree.body[:1]:
                raise AssertionError(f"forbidden migration construct: {type(node).__name__}")
    lowered = candidate_text.lower()
    for marker in ("/tests", "/logs", "subprocess", "socket", "requests.", "ridges_"):
        if marker in lowered:
            raise AssertionError(f"forbidden source marker: {marker}")
    return {
        "candidate_sha256": hashlib.sha256(candidate_text.encode()).hexdigest(),
        "fields": fields,
    }


def parse_test_run(result, expected_count, required_names):
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    if result.returncode:
        raise AssertionError(
            f"test command failed ({result.returncode}); tail={plain[-5000:]}"
        )
    if not re.search(rf"Ran {expected_count} tests?", plain):
        raise AssertionError(f"expected exactly {expected_count} tests")
    if not re.search(r"^OK$", plain, re.MULTILINE):
        raise AssertionError("test run did not finish OK")
    for name in required_names:
        if name not in plain:
            raise AssertionError(f"required test not reported: {name}")
    return plain


def focused_tests():
    result = run(
        [
            "python",
            "netbox/manage.py",
            "test",
            "netbox.tests.test_search.SearchBackendTestCase",
            "--keepdb",
            "--noinput",
            "--verbosity",
            "2",
        ],
        timeout=600,
        check=False,
    )
    plain = parse_test_run(
        result,
        6,
        ["test_cache_single_object", "test_remove_on_delete", "test_search"],
    )
    return {"tests": 6, "stdout_sha256": hashlib.sha256(plain.encode()).hexdigest()}


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
                "extras.tests.ridges_cached_value_index.CachedValueIndexHiddenTest",
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
    plain = parse_test_run(
        result,
        2,
        [
            "test_migration_state_matches_composite_model_index",
            "test_exact_object_delete_is_correct_and_selective",
        ],
    )
    marker = re.findall(r"RIDGES_INDEX_EVIDENCE=(\{[^\n]+\})", plain)
    if len(marker) != 1:
        raise AssertionError("missing exact PostgreSQL index evidence")
    evidence = json.loads(marker[0])
    if evidence.get("noise_rows") != 120000 or evidence.get("target_rows") != 7:
        raise AssertionError(f"wrong hidden world identity: {evidence}")
    evidence["stdout_sha256"] = hashlib.sha256(plain.encode()).hexdigest()
    return evidence


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
        lambda: hashlib.sha256(Path("/logs/verifier/graded.patch").read_bytes()).hexdigest(),
    )
    report.check("bounded_cached_value_index_migration", bounded_migration)
    report.check("source_tree_conservation_before_tests", source_identity)
    report.check(
        "python_compilation",
        lambda: compile((APP / ALLOWED).read_text(), str(ALLOWED), "exec") or "ok",
    )
    report.check(
        "ruff_lint",
        lambda: run(["ruff", "check", "--no-cache", str(ALLOWED)], timeout=120).returncode,
    )
    report.check("postgres_solver_role_is_bounded", role_identity)
    report.check("focused_upstream_search_backend_tests", focused_tests)
    before = schema_identity()
    report.check("hidden_cached_value_index_world", hidden_tests)
    report.check("source_tree_conservation_after_tests", source_identity)
    report.check(
        "database_schema_conservation",
        lambda: before
        if schema_identity() == before
        else (_ for _ in ()).throw(AssertionError("database schema changed")),
    )
    return report.write()


if __name__ == "__main__":
    sys.exit(main())
