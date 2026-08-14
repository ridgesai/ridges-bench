#!/bin/bash

JUNIT_XML="/logs/verifier/junit.xml"

rm -rf /logs/verifier/* 2>/dev/null || true
mkdir -p /logs/verifier

VDIR=$(mktemp -d)
trap 'rm -rf "$VDIR"' EXIT
export PYTHONPYCACHEPREFIX="$VDIR/pycache"
cp /tests/test_burndown_verification.py "$VDIR"/
cp /tests/test_aiosmtplib_smtp_message_preparation_contract.py "$VDIR"/
cp /tests/test_aiosmtplib_smtp_message_preparation_edge_cases.py "$VDIR"/
cp /tests/test_z_final_integrity.py "$VDIR"/
cp /tests/burndown_gates.py "$VDIR"/
cp /tests/baseline_manifest.json "$VDIR"/
: > "$VDIR/pytest.ini"

export REPO_ROOT=/app/src
export RUFF_BIN=/opt/venv/bin/ruff
export BASELINE_MANIFEST="$VDIR/baseline_manifest.json"
export GATES_MODULE="$VDIR/burndown_gates.py"
export PATCH_PREFLIGHT_ERROR="$VDIR/patch-preflight-error.txt"
export CHANGED_PATHS_FILE="$VDIR/changed-paths.z"
export FINAL_CHANGED_PATHS_FILE="$VDIR/final-changed-paths.z"

PATCH_COPY="$VDIR/candidate.patch"
CANONICAL_PATCH="$VDIR/reconstructed.patch"
export CANDIDATE_PATCH_FILE="$CANONICAL_PATCH"
: > "$PATCH_COPY"
: > "$CANONICAL_PATCH"
: > "$PATCH_PREFLIGHT_ERROR"
: > "$CHANGED_PATHS_FILE"
: > "$FINAL_CHANGED_PATHS_FILE"

git_repo() {
  git -c safe.directory="$REPO_ROOT" -C "$REPO_ROOT" "$@"
}

record_preflight_error() {
  printf '%s\n' "$1" >> "$PATCH_PREFLIGHT_ERROR"
}

if [ -f /logs/agent/patch.diff ]; then
  if ! cp /logs/agent/patch.diff "$PATCH_COPY"; then
    record_preflight_error "could not preserve /logs/agent/patch.diff"
  fi
else
  if ! git_repo add -A -- .; then
    record_preflight_error "could not stage the local agent workspace"
  elif ! git_repo diff --cached --binary --full-index HEAD > "$PATCH_COPY"; then
    record_preflight_error "could not synthesize the local agent patch"
  fi
fi

if ! git_repo reset --hard HEAD; then
  record_preflight_error "could not reset the repository to its baked baseline"
fi
if ! git_repo clean -ffdx; then
  record_preflight_error "could not remove files outside the submitted patch"
fi

if [ ! -s "$PATCH_PREFLIGHT_ERROR" ] && [ -s "$PATCH_COPY" ]; then
  if ! replay_error=$(git_repo apply --check "$PATCH_COPY" 2>&1); then
    record_preflight_error "submitted patch does not apply to the baked baseline: $replay_error"
  elif ! replay_error=$(git_repo apply "$PATCH_COPY" 2>&1); then
    record_preflight_error "could not replay the submitted patch: $replay_error"
  fi
fi

if [ ! -s "$PATCH_PREFLIGHT_ERROR" ]; then
  if ! git_repo add -A -- .; then
    record_preflight_error "could not stage the reconstructed candidate"
  elif ! git_repo diff --cached --name-only -z HEAD > "$CHANGED_PATHS_FILE"; then
    record_preflight_error "could not enumerate submitted patch paths"
  elif ! git_repo diff --cached --binary --full-index HEAD > "$CANONICAL_PATCH"; then
    record_preflight_error "could not capture the reconstructed candidate diff"
  fi
fi
if ! git_repo reset --mixed --quiet HEAD; then
  record_preflight_error "could not restore the repository index"
fi

cd "$VDIR"
env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /opt/venv/bin/python -I -X pycache_prefix="$VDIR/pycache" -m pytest \
  -xvs \
  -c "$VDIR/pytest.ini" \
  --confcutdir="$VDIR" \
  -p no:cacheprovider \
  -o junit_family=xunit1 \
  --junitxml="$JUNIT_XML" \
  "$VDIR"/test_burndown_verification.py \
  "$VDIR"/test_aiosmtplib_smtp_message_preparation_contract.py \
  "$VDIR"/test_aiosmtplib_smtp_message_preparation_edge_cases.py \
  "$VDIR"/test_z_final_integrity.py
test_status=$?

postflight_status=0
POSTFLIGHT_PATCH="$VDIR/postflight.patch"
if ! git_repo add -A -- .; then
  echo "POSTFLIGHT FAILURE: could not stage the tested workspace"
  postflight_status=1
elif ! git_repo diff --cached --binary --full-index HEAD > "$POSTFLIGHT_PATCH"; then
  echo "POSTFLIGHT FAILURE: could not capture the tested workspace diff"
  postflight_status=1
elif ! cmp -s "$CANONICAL_PATCH" "$POSTFLIGHT_PATCH"; then
  echo "POSTFLIGHT FAILURE: the submitted source diff changed during testing"
  postflight_status=1
elif ! /opt/venv/bin/python "$VDIR/burndown_gates.py" check "$REPO_ROOT" "$BASELINE_MANIFEST"; then
  postflight_status=1
fi
git_repo reset --mixed --quiet HEAD || postflight_status=1

if [ $test_status -eq 0 ] && [ $postflight_status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
if [ $test_status -ne 0 ]; then
  exit "$test_status"
fi
exit "$postflight_status"
