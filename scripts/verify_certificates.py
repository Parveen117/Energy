"""Verify every pinned certificate in results/ (Challenge-Engine
discipline from the Artificial-intelligence repo: the machinery audits
its own outputs). Recomputes each certificate's _pin from its content
and a canonical root over the whole results/ directory (device-repo
canonical_lock discipline)."""
from __future__ import annotations

import hashlib
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RES = os.path.join(ROOT, "results")


def sha256_of(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def main() -> int:
    ok = True
    entries = []
    for name in sorted(os.listdir(RES)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(RES, name)
        cert = json.load(open(path))
        if "_pin" in cert:
            recomputed = sha256_of({k: v for k, v in cert.items()
                                    if k != "_pin"})
            good = recomputed == cert["_pin"]
            ok &= good
            print(f"{'OK ' if good else 'BAD'} {name} pin={cert['_pin'][:16]}")
        else:
            print(f"--  {name} (no pin field)")
        entries.append((name, hashlib.sha256(
            open(path, "rb").read()).hexdigest()))
    root = hashlib.sha256(json.dumps(entries).encode()).hexdigest()
    print("results canonical root:", root)
    expected = os.path.join(RES, "CANONICAL_ROOT.txt")
    if os.path.exists(expected):
        want = open(expected).read().strip()
        if want != root:
            print(f"BAD canonical root: expected {want[:16]}...")
            ok = False
        else:
            print("OK  canonical root matches pinned value")
    else:
        open(expected, "w").write(root + "\n")
        print("pinned canonical root (first run)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
