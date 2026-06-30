#!/bin/bash

cd /app/src

export CI=true
export PYTHONUNBUFFERED=1

# Copy HEAD test files from /tests (overwrites BASE state)
mkdir -p "openhands-sdk/tests"
cp "/tests/openhands-sdk/tests/test_acp_agent_remote_mcp_headers.py" "openhands-sdk/tests/test_acp_agent_remote_mcp_headers.py"

test_status=0
/opt/venv/bin/python -m pytest \
  -o addopts= \
  -xvs \
  --tb=short \
  openhands-sdk/tests/test_acp_agent_remote_mcp_headers.py || test_status=$?

if [ $test_status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit "$test_status"
