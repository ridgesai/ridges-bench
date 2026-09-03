#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier
chmod 700 /logs/verifier /logs/agent /logs/artifacts
echo 0 > /logs/verifier/reward.txt
if [ ! -d /logs/artifacts ] || [ -L /logs/artifacts ]; then
  echo "invalid verifier artifact directory" >&2
  exit 1
fi
if ! find -P /logs/artifacts -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +; then
  echo "failed to clear verifier artifact directory" >&2
  exit 1
fi
if [ -n "$(find -P /logs/artifacts -mindepth 1 -maxdepth 1 -print -quit)" ]; then
  echo "verifier artifact directory is not empty" >&2
  exit 1
fi

if [ ! -e /logs/agent/patch.diff ]; then
  echo "missing transported patch" >&2
  exit 1
fi

cp /logs/agent/patch.diff /logs/verifier/graded.patch
chmod 400 /logs/verifier/graded.patch
cd /app
if [ -s /logs/verifier/graded.patch ]; then
  git apply --check /logs/verifier/graded.patch || exit 1
  git apply /logs/verifier/graded.patch || exit 1
fi
chown agent:agent /app/netbox/ipam/filtersets.py

python /tests/verify.py
status=$?
test -s /logs/verifier/reward.txt || echo 0 > /logs/verifier/reward.txt
exit "$status"
