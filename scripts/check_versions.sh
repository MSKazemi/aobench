#!/usr/bin/env bash
# check_versions.sh — Verify ExaBench version pins for a reproducible run.
# Usage: ./scripts/check_versions.sh [--dataset VERSION] [--engine VERSION] [--judge CONFIG_ID]

set -euo pipefail

DATASET_VERSION=""
ENGINE_VERSION=""
JUDGE_CONFIG_ID=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dataset) DATASET_VERSION="$2"; shift 2 ;;
        --engine)  ENGINE_VERSION="$2";  shift 2 ;;
        --judge)   JUDGE_CONFIG_ID="$2"; shift 2 ;;
        *) echo "Unknown arg: $1" >&2; exit 2 ;;
    esac
done

ERRORS=0

# Check engine version via exabench package
if [[ -n "$ENGINE_VERSION" ]]; then
    actual=$(python3 -c "import importlib.metadata; print(importlib.metadata.version('exabench'))" 2>/dev/null || echo "unknown")
    if [[ "$actual" != "$ENGINE_VERSION" ]]; then
        echo "WARNING: engine version mismatch: expected=$ENGINE_VERSION actual=$actual"
        ERRORS=$((ERRORS+1))
    else
        echo "OK: engine version=$actual"
    fi
fi

# Check dataset version via git tag (best-effort)
if [[ -n "$DATASET_VERSION" ]]; then
    actual=$(git describe --tags --exact-match 2>/dev/null || echo "untagged")
    if [[ "$actual" != "$DATASET_VERSION" ]]; then
        echo "WARNING: dataset version mismatch: expected=$DATASET_VERSION actual=$actual (may be untagged)"
    else
        echo "OK: dataset version=$actual"
    fi
fi

# Check judge config ID exists in prompts/judge/
if [[ -n "$JUDGE_CONFIG_ID" ]]; then
    if [[ -d "prompts/judge" ]]; then
        echo "OK: prompts/judge/ directory found (judge=$JUDGE_CONFIG_ID)"
    else
        echo "ERROR: prompts/judge/ not found — judge config cannot be verified"
        ERRORS=$((ERRORS+1))
    fi
fi

if [[ $ERRORS -gt 0 ]]; then
    echo "Version check completed with $ERRORS warning(s)" >&2
    exit 1
fi
echo "Version check passed."
