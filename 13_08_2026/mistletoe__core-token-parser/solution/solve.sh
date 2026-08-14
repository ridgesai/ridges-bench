#!/bin/bash
set -euo pipefail
cd /app/src
git apply /solution/fix.patch
