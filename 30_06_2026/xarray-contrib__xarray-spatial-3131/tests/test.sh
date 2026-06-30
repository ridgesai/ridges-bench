#!/bin/bash

cd /app/src

export CI=true
export MPLBACKEND=Agg
export NUMBA_ENABLE_CUDASIM=1
export NUMBA_CACHE_DIR=/tmp/numba-cache
export DASK_SCHEDULER=single-threaded

# Copy HEAD test files from /tests (overwrites BASE state)
mkdir -p "tests"
cp "/tests/test_rasterize_memory_contract_3107.py" "tests/test_rasterize_memory_contract_3107.py"

/opt/venv/bin/python -m pytest -xvs "tests/test_rasterize_memory_contract_3107.py"
test_status=$?

if [ $test_status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit "$test_status"
