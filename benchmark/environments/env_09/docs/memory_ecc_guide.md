# Memory ECC Error Guide

## ECC error types
- **Correctable (CE):** Single-bit errors, corrected by hardware. Logged but non-fatal.
- **Uncorrectable (UE):** Multi-bit errors, cause system crash or memory corruption.

## Thresholds
- CE threshold for alerting: >50 per hour on any DIMM
- CE threshold for drain: >200 per hour (indicates failing DIMM)
- Any UE: immediate drain and offline

## Diagnosis
1. Check SLURM node state — is the node draining or drained?
2. Query telemetry for memory error events.
3. Run on the node: `edac-util -s 0` to see per-DIMM error counts.
4. Run `mcelog` to see detailed CPU/memory machine check events.

## Remediation
- Replace failing DIMM with spare.
- Test with `memtest86+` before returning to service.
- Document DIMM slot and replacement in asset management.
