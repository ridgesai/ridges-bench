#!/bin/bash

cd /app/src

export PYTHONUNBUFFERED=1

# Copy HEAD test files from /tests (overwrites BASE state)
mkdir -p "tests"
cp "/tests/test_oracle_db_url_descriptors.py" "tests/test_oracle_db_url_descriptors.py"

/opt/venv/bin/pytest -xvs tests/test_oracle_db_url_descriptors.py
test_status=$?

if [ $test_status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit "$test_status"
