#!/bin/bash

cd /app/src

export CI=true
export PYTHONUNBUFFERED=1

# Copy HEAD test files from /tests (overwrites BASE state)
mkdir -p "tests/sdk/llm"
cp "/tests/sdk/llm/test_llm_custom_tokenizer_contract.py" "tests/sdk/llm/test_llm_custom_tokenizer_contract.py"

test_status=0
/opt/venv/bin/python -m pytest \
  -o addopts= \
  -xvs \
  --tb=short \
  tests/sdk/llm/test_llm_custom_tokenizer_contract.py || test_status=$?

if [ $test_status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit "$test_status"
