"""Contracts for absent and valid flattened JWS signatures."""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(os.environ["REPO_ROOT"])
sys.path.insert(0, str(REPO_ROOT / "src"))

import joserfc._rfc7515.json as json_module
from joserfc._rfc7515.json import verify_flattened_json
from joserfc._rfc7515.model import FlattenedJSONSignature, HeaderMember
from joserfc._rfc7515.registry import JWSRegistry
from joserfc.jwk import OctKey
from joserfc.jws import deserialize_json, serialize_json


def _unsigned_object():
    obj = FlattenedJSONSignature(HeaderMember(), b"payload")
    obj.segments["payload"] = b"cGF5bG9hZA"
    return obj


def test_absent_signature_returns_false_without_verification_or_key_lookup(monkeypatch):
    calls = []

    def verify_signature(*_args, **_kwargs):
        calls.append("verification")
        raise AssertionError("algorithm verification must not run without a signature")

    def find_key(_member):
        calls.append("key lookup")
        raise AssertionError("key lookup must not run without a signature")

    monkeypatch.setattr(json_module, "verify_signature", verify_signature)
    assert verify_flattened_json(_unsigned_object(), JWSRegistry(), find_key) is False
    assert calls == []


def test_absent_signature_has_same_result_under_optimized_python():
    code = r"""
import joserfc._rfc7515.json as json_module
from joserfc._rfc7515.json import verify_flattened_json
from joserfc._rfc7515.model import FlattenedJSONSignature, HeaderMember
from joserfc._rfc7515.registry import JWSRegistry

obj = FlattenedJSONSignature(HeaderMember(), b"payload")
obj.segments["payload"] = b"cGF5bG9hZA"

def verify_signature(*_args, **_kwargs):
    raise RuntimeError("algorithm verification ran")

json_module.verify_signature = verify_signature

def find_key(_member):
    raise RuntimeError("key lookup ran")

result = verify_flattened_json(obj, JWSRegistry(), find_key)
if result is not False:
    raise SystemExit(f"unexpected verification result: {result!r}")
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    proc = subprocess.run(
        [sys.executable, "-O", "-c", code],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_valid_flattened_signature_still_round_trips_and_tampering_fails():
    key = OctKey.import_key("a sufficiently long shared secret")
    encoded = serialize_json({"protected": {"alg": "HS256"}}, b"hello", key)
    decoded = deserialize_json(encoded, key)
    assert decoded.payload == b"hello"

    encoded["payload"] = "dGFtcGVyZWQ"
    try:
        deserialize_json(encoded, key)
    except Exception:
        pass
    else:
        raise AssertionError("a tampered payload must not verify")
