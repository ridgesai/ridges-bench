#!/bin/bash

cd /app/src

export CI=true
export DATAMODEL_CODE_GENERATOR_TEST_DEFAULT_FORMATTER=builtin

mkdir -p "tests/parser"
cp "/tests/parser/test_collapse_root_models_split_oneof.py" "tests/parser/test_collapse_root_models_split_oneof.py"

pytest -xvs tests/parser/test_collapse_root_models_split_oneof.py
test_status=$?

if [ $test_status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit "$test_status"
