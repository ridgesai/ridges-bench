#!/bin/bash

cd /app/src

export CI=true
export PYTHONUNBUFFERED=1

# Copy HEAD test files from /tests (overwrites BASE state)
mkdir -p "openhands-tools/tests"
cp "/tests/openhands-tools/tests/test_terminal_pager_behavior.py" "openhands-tools/tests/test_terminal_pager_behavior.py"

test_status=0
/opt/venv/bin/python -m pytest \
  -o addopts= \
  -xvs \
  --tb=short \
  openhands-tools/tests/test_terminal_pager_behavior.py || test_status=$?

if [ $test_status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit "$test_status"
