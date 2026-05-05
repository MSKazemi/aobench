#!/usr/bin/env python3
"""Trace diff utility for AOBench reproducibility verification.

Compares two trace JSON files, ignoring whitelisted fields.
Exits 0 if traces are equivalent, 1 if differences found, 2 on usage error.
"""

import argparse
import json
import math
import sys
from pathlib import Path

WHITELIST = {
    "run_id", "started_at", "ended_at", "api_request_id",
    "trace_id", "created_at", "updated_at",
}

def remove_whitelisted(obj, whitelist=WHITELIST):
    """Recursively remove whitelisted keys from a nested dict/list."""
    if isinstance(obj, dict):
        return {k: remove_whitelisted(v, whitelist) for k, v in obj.items() if k not in whitelist}
    if isinstance(obj, list):
        return [remove_whitelisted(item, whitelist) for item in obj]
    return obj

def floats_equal(a, b, rel_tol=1e-9):
    if isinstance(a, float) and isinstance(b, float):
        if math.isnan(a) and math.isnan(b):
            return True
        return math.isclose(a, b, rel_tol=rel_tol)
    return a == b

def deep_diff(a, b, path=""):
    """Return list of difference descriptions."""
    diffs = []
    if type(a) != type(b):
        # Allow int/float comparison
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if not floats_equal(float(a), float(b)):
                diffs.append(f"{path}: {a!r} != {b!r}")
        else:
            diffs.append(f"{path}: type {type(a).__name__} != {type(b).__name__}")
        return diffs
    if isinstance(a, dict):
        all_keys = set(a) | set(b)
        for k in sorted(all_keys):
            child = f"{path}.{k}" if path else k
            if k not in a:
                diffs.append(f"{child}: missing in trace_a")
            elif k not in b:
                diffs.append(f"{child}: missing in trace_b")
            else:
                diffs.extend(deep_diff(a[k], b[k], child))
    elif isinstance(a, list):
        if len(a) != len(b):
            diffs.append(f"{path}: list length {len(a)} != {len(b)}")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                diffs.extend(deep_diff(x, y, f"{path}[{i}]"))
    elif isinstance(a, float) or isinstance(b, float):
        if not floats_equal(float(a), float(b)):
            diffs.append(f"{path}: {a!r} != {b!r}")
    else:
        if a != b:
            diffs.append(f"{path}: {a!r} != {b!r}")
    return diffs

def main():
    ap = argparse.ArgumentParser(description="Compare two AOBench trace JSON files.")
    ap.add_argument("trace_a", help="Path to first trace JSON file")
    ap.add_argument("trace_b", help="Path to second trace JSON file")
    ap.add_argument("--whitelist", nargs="*", default=[], help="Additional fields to ignore")
    args = ap.parse_args()

    try:
        a = json.loads(Path(args.trace_a).read_text())
        b = json.loads(Path(args.trace_b).read_text())
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    whitelist = WHITELIST | set(args.whitelist)
    a_clean = remove_whitelisted(a, whitelist)
    b_clean = remove_whitelisted(b, whitelist)

    diffs = deep_diff(a_clean, b_clean)
    if diffs:
        print(f"DIFF: {len(diffs)} difference(s) found")
        for d in diffs:
            print(f"  {d}")
        sys.exit(1)
    else:
        print("MATCH: traces are equivalent (modulo whitelisted fields)")
        sys.exit(0)

if __name__ == "__main__":
    main()
