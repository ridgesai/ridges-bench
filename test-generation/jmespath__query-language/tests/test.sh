#!/bin/bash
# Sample verifier (public ridges-bench samples). Runs the submitted regression
# suite against the unmodified library and against a set of modified copies:
#   - mutants: small behavioral bugs; the suite must FAIL on each one;
#   - decoys:  behavior-preserving rewrites; the suite must PASS on each one.
# Reward is 1 only if the suite passes on the original, passes on every decoy
# and fails on every mutant.
set -uo pipefail

# shellcheck source=/dev/null
source /tests/sample.env   # IMPORT_NAME, MUTANTS, DECOYS

mkdir -p /logs/verifier
chmod 700 /logs /logs/verifier
# Per-cell reports stay in a root-only directory while suites run (bind-mounted /logs may not enforce
# permissions on every host); they are copied into /logs/verifier only after the last cell.
CELLS=/var/lib/verifier-cells
rm -rf "$CELLS"; mkdir -m 700 -p "$CELLS"
rm -f /logs/verifier/junit.xml
echo 0 > /logs/verifier/reward.txt

cd /app
if [ ! -s /logs/agent/patch.diff ]; then
  echo "submitted patch is missing or empty" >&2
  exit 1
fi
cp /logs/agent/patch.diff /logs/verifier/graded.patch
git apply --check /logs/verifier/graded.patch || exit 1

# Only files under regression_tests/ may be added or changed.
badpath=0
while IFS=$'\t' read -r -d '' _added _removed path; do
  case "$path" in
    regression_tests/*) ;;
    *) echo "path outside regression_tests: $path" >&2; badpath=1 ;;
  esac
done < <(git apply --numstat -z /logs/verifier/graded.patch)
[ "$badpath" -eq 0 ] || exit 1
git apply /logs/verifier/graded.patch || exit 1

# The suite runs as an unprivileged user and sees only its own copy of the library:
# the variant tree, the verifier files and the pristine checkout stay root-only.
chmod -R go-rwx /matrix /tests /app 2>/dev/null || true

# Run the suite against one variant of the library. Every variant is loaded
# from the same path, /work/src, so the suite sees an identical layout.
declare -A CELL_RC
run_cell() {
  local state="$1"
  CELL_RC[$state]=invalid
  rm -rf /work
  find -P /tmp /var/tmp /dev/shm -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + 2>/dev/null || true
  mkdir -p /work/tmp /work/out
  cp -r "/matrix/${state}/src" /work/src
  cp -r /app/regression_tests /work/regression_tests
  chmod -R a+rX,go-w /work/src /work/regression_tests
  chown -R nobody /work/tmp /work/out
  chmod 755 /work
  (cd /work && PYTHONPATH=/work/src python -c "import ${IMPORT_NAME}, sys; sys.exit(0 if ${IMPORT_NAME}.__file__.startswith('/work/src/') else 7)") || {
    echo "a library copy did not load from /work/src" >&2
    CELL_RC[$state]=7
    return 7
  }
  timeout -k 5 60 su -s /bin/bash nobody -c "cd /work && HOME=/work/tmp TMPDIR=/work/tmp PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/work/src python -m pytest /work/regression_tests -q -p no:cacheprovider -c /dev/null --rootdir=/work --junitxml=/work/out/junit.xml" > /dev/null 2>&1
  local rc=$?
  CELL_RC[$state]=$rc
  # Stop anything the suite left running before reading its report.
  su -s /bin/bash nobody -c "kill -9 -1" > /dev/null 2>&1 || true
  [ -f /work/out/junit.xml ] && cp /work/out/junit.xml "$CELLS/cell-${state}.xml"
  return $rc
}

# "tests failures errors id-set-sha256" from a cell report; empty output means no usable
# report. The id set is every testcase's "classname::name", sorted.
cell_counts() {
  python - "$CELLS/cell-$1.xml" <<'PYEOF'
import hashlib, sys, xml.etree.ElementTree as ET
try:
    root = ET.parse(sys.argv[1]).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    ids = sorted(
        "{}::{}".format(tc.get("classname") or "", tc.get("name") or "")
        for tc in suite.iter("testcase")
    )
    print(suite.get("tests"), suite.get("failures"), suite.get("errors"),
          hashlib.sha256("\n".join(ids).encode()).hexdigest())
except Exception:
    pass
PYEOF
}

declare -A verdict
classify() { # state, expected (green|red)
  local state="$1" want="$2" t f e ids rc
  rc="${CELL_RC[$state]:-}"
  # Only a normal pytest exit is a verdict: 0 (all passed) or 1 (tests failed). A timeout,
  # a collection error, an internal or usage error, or "no tests ran" is not.
  if [ "$rc" != 0 ] && [ "$rc" != 1 ]; then verdict[$state]=invalid; return; fi
  read -r t f e ids <<< "$(cell_counts "$state")"
  # A usable report must exist and collect the same set of tests as the original.
  if [ -z "${t:-}" ] || [ "$t" != "$BASE_TESTS" ] || [ "${ids:-}" != "$BASE_IDS" ]; then
    verdict[$state]=invalid; return
  fi
  if [ "$want" = green ]; then
    [ $((f + e)) -eq 0 ] && verdict[$state]=ok || verdict[$state]=wrong
  else
    [ $((f + e)) -ge 1 ] && verdict[$state]=ok || verdict[$state]=wrong
  fi
}

run_cell pristine
read -r BASE_TESTS _ _ BASE_IDS <<< "$(cell_counts pristine)"
if [ -z "${BASE_TESTS:-}" ] || [ "$BASE_TESTS" -lt 1 ]; then
  echo "no valid test report on the original library" >&2
  exit 1
fi
classify pristine green
# The modified copies run in random order; verdicts are reported in a fixed order.
for s in $(printf '%s\n' $DECOYS $MUTANTS | shuf); do run_cell "$s"; done
for s in $DECOYS; do classify "$s" green; done
for s in $MUTANTS; do classify "$s" red; done

cp "$CELLS"/cell-*.xml /logs/verifier/ 2>/dev/null || true

failures=0; rows=""
row() { # name, state
  local v="${verdict[$2]}"
  if [ "$v" = ok ]; then
    rows="${rows}  <testcase classname=\"matrix\" name=\"$1\"/>"$'\n'
  else
    failures=$((failures + 1))
    rows="${rows}  <testcase classname=\"matrix\" name=\"$1\"><failure message=\"cell verdict $v\"/></testcase>"$'\n'
  fi
}
row original_passes pristine
for s in $DECOYS; do row "${s}_passes" "$s"; done
for s in $MUTANTS; do row "${s}_caught" "$s"; done
n=$(printf '%s' "$rows" | grep -c '<testcase')
{
  echo '<?xml version="1.0" encoding="utf-8"?>'
  printf '<testsuite name="sample-matrix" tests="%d" failures="%d" errors="0" skipped="0">\n' "$n" "$failures"
  printf '%s' "$rows"
  echo '</testsuite>'
} > /logs/verifier/junit.xml

if [ "$failures" -eq 0 ]; then echo 1 > /logs/verifier/reward.txt; exit 0; fi
exit 1
