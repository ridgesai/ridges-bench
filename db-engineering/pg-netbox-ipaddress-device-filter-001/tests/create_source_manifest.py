#!/usr/bin/env python3
import hashlib
import json
import stat
from pathlib import Path

root = Path("/app")
allowed = Path("netbox/ipam/filtersets.py")
entries = {}

for path in sorted(root.rglob("*")):
    relative = path.relative_to(root)
    if not relative.parts or relative == allowed:
        continue
    mode = stat.S_IMODE(path.lstat().st_mode)
    if path.is_symlink():
        entries[str(relative)] = {
            "kind": "symlink",
            "mode": mode,
            "target": path.readlink().as_posix(),
        }
    elif path.is_file():
        entries[str(relative)] = {
            "kind": "file",
            "mode": mode,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    elif path.is_dir():
        entries[str(relative)] = {"kind": "directory", "mode": mode}
    else:
        raise SystemExit(f"unexpected source-tree entry: {relative}")

protected = Path("/opt/task")
protected.mkdir(parents=True, exist_ok=True)
protected.joinpath("source-manifest.json").write_text(
    json.dumps(entries, sort_keys=True, separators=(",", ":")) + "\n"
)
protected.joinpath("original-filtersets.py").write_bytes(
    root.joinpath(allowed).read_bytes()
)
protected.joinpath("allowed-metadata.json").write_text(
    json.dumps({"kind": "file", "mode": 0o644}, sort_keys=True) + "\n"
)
protected.joinpath("SOURCE_REVISION").write_text(
    "00791344e68213bde942218283dce03cc3941c30\n"
)
