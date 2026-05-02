#!/usr/bin/env python3
"""Compute SHA-256 of every file in each snapshot bundle and write data/snapshots/MANIFEST.json."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ENV_ROOT = Path("benchmark/environments")
OUTPUT = Path("data/snapshots/MANIFEST.json")


def hash_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_tracked_envs(root: Path) -> set[str]:
    import subprocess
    result = subprocess.run(
        ["git", "ls-files", str(root)],
        capture_output=True, text=True
    )
    envs = set()
    for line in result.stdout.splitlines():
        parts = line.split("/")
        # path is like: benchmark/environments/env_NN/...
        for i, part in enumerate(parts):
            if part.startswith("env_"):
                envs.add(part)
                break
    return envs


def main() -> None:
    tracked = _git_tracked_envs(ENV_ROOT)
    environments = {}
    for env_dir in sorted(ENV_ROOT.iterdir()):
        if not env_dir.is_dir() or not env_dir.name.startswith("env_"):
            continue
        if env_dir.name not in tracked:
            continue
        files = {}
        for p in sorted(env_dir.rglob("*")):
            if p.is_file():
                files[str(p.relative_to(env_dir))] = hash_file(p)
        environments[env_dir.name] = files

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_version": "exabench-v0.2.0",
        "total_envs": len(environments),
        "total_files": sum(len(v) for v in environments.values()),
        "environments": environments,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"Wrote manifest: {len(environments)} envs, {manifest['total_files']} files")


if __name__ == "__main__":
    main()
