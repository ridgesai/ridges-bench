#!/bin/bash

cd /app/src

export CI=true
export DATAMODEL_CODE_GENERATOR_TEST_DEFAULT_FORMATTER=builtin

# Copy HEAD test files from /tests (overwrites BASE state)
mkdir -p "tests"
cp "/tests/test_pydantic_base_field_strip_default_none.py" "tests/test_pydantic_base_field_strip_default_none.py"

pytest -xvs tests/test_pydantic_base_field_strip_default_none.py
test_status=$?

if [ $test_status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit "$test_status"
