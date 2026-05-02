#!/usr/bin/env python3
"""Verify snapshot file hashes match data/snapshots/MANIFEST.json."""
import hashlib
import json
import pathlib
import sys

MANIFEST_PATH = pathlib.Path("data/snapshots/MANIFEST.json")
ENV_ROOT = pathlib.Path("benchmark/environments")


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not MANIFEST_PATH.exists():
        print(f"ERROR: manifest not found: {MANIFEST_PATH}", file=sys.stderr)
        return 1

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    environments: dict[str, dict[str, str]] = manifest.get("environments", {})
    if not environments:
        print("ERROR: manifest contains no environments", file=sys.stderr)
        return 1

    mismatches: list[str] = []
    total_files = 0

    for env_name, files in sorted(environments.items()):
        env_dir = ENV_ROOT / env_name
        for rel_path, expected_hash in files.items():
            full_path = env_dir / rel_path
            if not full_path.exists():
                print(f"MISSING: {env_name}/{rel_path}", file=sys.stderr)
                mismatches.append(f"{env_name}/{rel_path}")
                continue
            actual_hash = sha256_file(full_path)
            if actual_hash != expected_hash:
                print(f"MISMATCH: {env_name}/{rel_path}")
                mismatches.append(f"{env_name}/{rel_path}")
            total_files += 1

    num_envs = len(environments)
    print(f"verified {total_files} files across {num_envs} environments")

    if mismatches:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
