#!/bin/bash

cd /app/src

export CI=true
export DATAMODEL_CODE_GENERATOR_TEST_DEFAULT_FORMATTER=builtin

mkdir -p "tests/parser"
cp "/tests/parser/test_recursive_forward_refs.py" "tests/parser/test_recursive_forward_refs.py"

pytest -xvs tests/parser/test_recursive_forward_refs.py
test_status=$?

if [ $test_status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit "$test_status"
