"""run_ollama_batch.py — Run all pending Ollama models smallest-first.

Opens the SSH tunnel, checks which models already have complete runs,
then runs each pending model in sequence.

Usage:
    uv run python scripts/run_ollama_batch.py [--dry-run]
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import threading
import socket
from pathlib import Path

# Add project root to path so we can import ollama_tunnel
sys.path.insert(0, str(Path(__file__).parent))
from ollama_tunnel import open_tunnel  # noqa: E402

# ── Config ─────────────────────────────────────────────────────────────────────

OUTPUT_DIR = "data/runs/v02_dev_ollama"
SPLIT = "dev"
MIN_RESULTS = 55  # treat run as complete if it has >= this many result files

# Models ordered smallest → largest (GB), with skip reasons where applicable
MODELS = [
    # ("glm-ocr:latest",            "skip: OCR-specialised model"),
    ("mistral-nemo:latest",        None),   # 7.1 GB
    ("gemma4:e4b",                 None),   # 9.6 GB
    ("gpt-oss:latest",             None),   # 13.8 GB
    ("gpt-oss:20b",                None),   # 13.8 GB
    ("devstral-small-2:24b",       None),   # 15.2 GB
    ("GLM-4.7-Flash:latest",       None),   # 19.0 GB
    ("gemma4:31b",                 None),   # 19.9 GB
    ("qwen3.6:35b-a3b",            None),   # 23.9 GB  (may need re-run)
    ("mistral-small:24b",          None),   # 14.3 GB  (done per memory — will skip if complete)
    ("nemotron3:33b",              None),   # 27.6 GB  (done per memory — will skip if complete)
    ("qwen3-coder-next:latest",    None),   # 51.7 GB
    ("qwen3.5:122b",               None),   # 81.4 GB  (done per memory — will skip if complete)
    ("nemotron-3-super:latest",    None),   # 86.8 GB
    # ("gpt-oss:120b",             "skip: 65 GB, too large"),
    # ("mistral-medium-3.5:latest","skip: >35 min/task"),
]


def count_results(model: str) -> int:
    """Count completed result JSON files for this model under OUTPUT_DIR.

    aobench multi-model path writes to: <output>/<model_token>/run_*/results/*.json
    """
    model_dir = Path(OUTPUT_DIR) / model
    if not model_dir.exists():
        return 0
    return len(list(model_dir.rglob("*_result.json")))


def run_model(model: str, dry_run: bool = False) -> int:
    """Run aobench for one model. Returns subprocess returncode."""
    env = os.environ.copy()
    env["OLLAMA_BASE_URL"] = "http://localhost:11434"
    env["LLM_PROVIDER"] = "ollama"

    cmd = [
        "uv", "run", "aobench", "run", "all",
        "--split", SPLIT,
        "--models", model,
        "--output", OUTPUT_DIR,
        "--langfuse",
    ]
    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Running: {' '.join(cmd)}", flush=True)
    if dry_run:
        return 0
    result = subprocess.run(cmd, env=env)
    return result.returncode


def wait_for_ollama(port: int = 11434, timeout: int = 10) -> bool:
    """Probe localhost:<port>/api/tags to confirm Ollama is reachable."""
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://localhost:{port}/api/tags", timeout=3) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    print("[batch] Opening SSH tunnel …", flush=True)
    ssh, server_sock, stop_event = open_tunnel()
    time.sleep(1.0)

    if not wait_for_ollama():
        print("[batch] ERROR: Ollama not reachable after tunnel open.", file=sys.stderr)
        stop_event.set(); server_sock.close(); ssh.close()
        sys.exit(1)
    print("[batch] Tunnel ready. Starting model runs.", flush=True)

    results_summary: list[dict] = []

    try:
        for model, skip_reason in MODELS:
            if skip_reason:
                print(f"\n[batch] SKIP {model}: {skip_reason}", flush=True)
                continue

            n = count_results(model)
            if n >= MIN_RESULTS:
                print(f"\n[batch] SKIP {model}: already complete ({n} results)", flush=True)
                results_summary.append({"model": model, "status": "skipped", "results": n})
                continue

            if n > 0:
                print(f"\n[batch] {model}: {n} results found — incomplete, re-running", flush=True)
            else:
                print(f"\n[batch] {model}: no results — running fresh", flush=True)

            rc = run_model(model, dry_run=dry_run)
            status = "ok" if rc == 0 else f"error(rc={rc})"
            results_summary.append({"model": model, "status": status, "results": count_results(model)})
            print(f"[batch] {model} → {status}", flush=True)

    finally:
        stop_event.set()
        server_sock.close()
        ssh.close()

    print("\n\n=== Batch summary ===")
    for r in results_summary:
        print(f"  {r['model']:40s}  {r['status']}  ({r['results']} results)")


if __name__ == "__main__":
    main()
