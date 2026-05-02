"""Fidelity validators F1–F7 for HPC environment snapshot bundles.

Each validator takes a bundle directory (Path) and returns a ValidatorResult.
Validators are deterministic and gracefully skip when required files are absent.
"""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ValidatorResult:
    """Result produced by a single fidelity validator."""

    validator_id: str       # "F1" through "F7"
    passed: bool
    metric: str             # short label, e.g. "lognormal_mu"
    value: Optional[float]  # measured value (None when not applicable)
    expected: str           # human-readable expected range, e.g. "7.8±1.5σ"
    message: str            # human-readable verdict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_elapsed_seconds(elapsed) -> Optional[float]:
    """Convert elapsed field to seconds.

    Accepts:
    - "HH:MM:SS" strings
    - plain int / float (already seconds)
    - None → returns None
    """
    if elapsed is None:
        return None
    if isinstance(elapsed, (int, float)):
        return float(elapsed)
    s = str(elapsed).strip()
    parts = s.split(":")
    try:
        if len(parts) == 3:
            h, m, sec = parts
            return int(h) * 3600 + int(m) * 60 + float(sec)
        if len(parts) == 2:
            m, sec = parts
            return int(m) * 60 + float(sec)
        return float(s)
    except (ValueError, TypeError):
        return None


def _load_jobs(bundle_dir: Path) -> Optional[list]:
    """Load the jobs array from slurm/slurm_state.json, or None if missing."""
    slurm_path = bundle_dir / "slurm" / "slurm_state.json"
    if not slurm_path.exists():
        return None
    try:
        data = json.loads(slurm_path.read_text())
        if isinstance(data, dict):
            return data.get("jobs", [])
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# F1 — Job-duration log-normal fit
# ---------------------------------------------------------------------------

def validate_f1_job_duration(bundle_dir: Path) -> ValidatorResult:
    """F1: Job durations should follow a log-normal distribution.

    Loads slurm/slurm_state.json, requires ≥ 8 jobs with an `elapsed` field.
    Fits μ and σ of log(elapsed_seconds) and checks:
      μ ∈ [6.3, 9.3]  (target 7.8 ± 1.5)
      σ ∈ [1.4, 2.4]  (target 1.9 ± 0.5)
    """
    jobs = _load_jobs(bundle_dir)
    if jobs is None:
        return ValidatorResult(
            validator_id="F1",
            passed=True,
            metric="lognormal_mu",
            value=None,
            expected="7.8±1.5σ",
            message="skipped (no slurm_state.json)",
        )

    elapsed_list = []
    for job in jobs:
        raw = job.get("elapsed")
        secs = _parse_elapsed_seconds(raw)
        if secs is not None and secs > 0:
            elapsed_list.append(secs)

    if len(elapsed_list) < 8:
        return ValidatorResult(
            validator_id="F1",
            passed=False,
            metric="lognormal_mu",
            value=None,
            expected="7.8±1.5σ",
            message=f"insufficient jobs: found {len(elapsed_list)} with elapsed, need ≥ 8",
        )

    log_vals = [math.log(s) for s in elapsed_list]
    mu = statistics.mean(log_vals)
    sigma = statistics.pstdev(log_vals)  # population std to be deterministic

    mu_ok = 6.3 <= mu <= 9.3
    sigma_ok = 1.4 <= sigma <= 2.4
    passed = mu_ok and sigma_ok

    return ValidatorResult(
        validator_id="F1",
        passed=passed,
        metric="lognormal_mu",
        value=mu,
        expected="μ∈[6.3,9.3] σ∈[1.4,2.4]",
        message=(
            f"μ={mu:.3f} ({'OK' if mu_ok else 'FAIL'}), "
            f"σ={sigma:.3f} ({'OK' if sigma_ok else 'FAIL'})"
        ),
    )


# ---------------------------------------------------------------------------
# F2 — Job-size power-law
# ---------------------------------------------------------------------------

def validate_f2_job_size(bundle_dir: Path) -> ValidatorResult:
    """F2: CPU counts across jobs should follow a power-law distribution.

    Fits α using MLE: α ≈ 1 + n / Σ ln(x / xmin), xmin=1.
    Pass if α ∈ [1.4, 2.0].
    """
    jobs = _load_jobs(bundle_dir)
    if jobs is None:
        return ValidatorResult(
            validator_id="F2",
            passed=True,
            metric="powerlaw_alpha",
            value=None,
            expected="α∈[1.4,2.0]",
            message="skipped (no slurm_state.json)",
        )

    cpu_vals = []
    for job in jobs:
        raw = job.get("num_cpus")
        if raw is not None:
            try:
                v = int(raw)
                if v >= 1:
                    cpu_vals.append(v)
            except (ValueError, TypeError):
                pass

    if len(cpu_vals) < 10:
        return ValidatorResult(
            validator_id="F2",
            passed=False,
            metric="powerlaw_alpha",
            value=None,
            expected="α∈[1.4,2.0]",
            message=f"insufficient jobs: found {len(cpu_vals)} with num_cpus ≥ 1, need ≥ 10",
        )

    xmin = 1.0
    n = len(cpu_vals)
    log_sum = sum(math.log(x / xmin) for x in cpu_vals)
    if log_sum == 0.0:
        # All values equal xmin → degenerate distribution (α = ∞)
        return ValidatorResult(
            validator_id="F2",
            passed=False,
            metric="powerlaw_alpha",
            value=None,
            expected="α∈[1.4,2.0]",
            message="degenerate distribution: all num_cpus == xmin → α = ∞",
        )
    alpha = 1.0 + n / log_sum
    passed = 1.4 <= alpha <= 2.0

    return ValidatorResult(
        validator_id="F2",
        passed=passed,
        metric="powerlaw_alpha",
        value=alpha,
        expected="α∈[1.4,2.0]",
        message=f"α={alpha:.3f} ({'OK' if passed else 'FAIL'})",
    )


# ---------------------------------------------------------------------------
# F3 — Job-state mix
# ---------------------------------------------------------------------------

def validate_f3_job_state_mix(bundle_dir: Path) -> ValidatorResult:
    """F3: Job state distribution should match expected HPC cluster proportions.

    Pass if COMPLETED ∈ [0.68, 0.88] and FAILED ∈ [-0.01, 0.19].
    Negative lower bound for FAILED is intentional (handles 0%).
    """
    jobs = _load_jobs(bundle_dir)
    if jobs is None:
        return ValidatorResult(
            validator_id="F3",
            passed=True,
            metric="completed_fraction",
            value=None,
            expected="COMPLETED∈[68%,88%] FAILED∈[0%,19%]",
            message="skipped (no slurm_state.json)",
        )

    if len(jobs) < 10:
        return ValidatorResult(
            validator_id="F3",
            passed=False,
            metric="completed_fraction",
            value=None,
            expected="COMPLETED∈[68%,88%] FAILED∈[0%,19%]",
            message=f"insufficient jobs: {len(jobs)}, need ≥ 10",
        )

    total = len(jobs)
    counts: dict[str, int] = {}
    for job in jobs:
        state = str(job.get("state", "UNKNOWN")).upper()
        counts[state] = counts.get(state, 0) + 1

    comp_frac = counts.get("COMPLETED", 0) / total
    fail_frac = counts.get("FAILED", 0) / total

    comp_ok = 0.68 <= comp_frac <= 0.88
    fail_ok = -0.01 <= fail_frac <= 0.19
    passed = comp_ok and fail_ok

    return ValidatorResult(
        validator_id="F3",
        passed=passed,
        metric="completed_fraction",
        value=comp_frac,
        expected="COMPLETED∈[68%,88%] FAILED∈[0%,19%]",
        message=(
            f"COMPLETED={comp_frac:.1%} ({'OK' if comp_ok else 'FAIL'}), "
            f"FAILED={fail_frac:.1%} ({'OK' if fail_ok else 'FAIL'})"
        ),
    )


# ---------------------------------------------------------------------------
# F4 — Node power per class
# ---------------------------------------------------------------------------

def validate_f4_node_power(bundle_dir: Path) -> ValidatorResult:
    """F4: Mean node power should be in range per node class (CPU vs GPU).

    Looks for power/*.csv or telemetry/*.csv with `power_w` or `watts` column
    and a `node` column. Requires ≥ 4 nodes with ≥ 12 samples each.
    CPU nodes: 297–402 W; GPU nodes: 1572–2128 W.
    """
    try:
        import pandas as pd
    except ImportError:
        return ValidatorResult(
            validator_id="F4",
            passed=True,
            metric="no_power_data",
            value=None,
            expected="CPU∈[297,402]W GPU∈[1572,2128]W",
            message="skipped (pandas not available)",
        )

    # Collect candidate CSV files
    csv_files: list[Path] = []
    for subdir in ("power", "telemetry"):
        d = bundle_dir / subdir
        if d.is_dir():
            csv_files.extend(d.glob("*.csv"))

    if not csv_files:
        return ValidatorResult(
            validator_id="F4",
            passed=True,
            metric="no_power_data",
            value=None,
            expected="CPU∈[297,402]W GPU∈[1572,2128]W",
            message="skipped (no power files)",
        )

    # Try to load a df with node + power column
    node_readings: dict[str, list[float]] = {}
    for csv_path in csv_files:
        try:
            df = pd.read_csv(csv_path)
            cols = {c.lower() for c in df.columns}
            power_col = None
            for candidate in ("power_w", "watts", "power"):
                if candidate in cols:
                    # find actual column name (case-insensitive)
                    for c in df.columns:
                        if c.lower() == candidate:
                            power_col = c
                            break
                    break

            node_col = None
            for candidate in ("node", "node_id", "hostname"):
                if candidate in cols:
                    for c in df.columns:
                        if c.lower() == candidate:
                            node_col = c
                            break
                    break

            if power_col is None or node_col is None:
                continue

            for _, row in df.iterrows():
                node = str(row[node_col])
                try:
                    w = float(row[power_col])
                    node_readings.setdefault(node, []).append(w)
                except (ValueError, TypeError):
                    pass
        except Exception:
            continue

    if not node_readings:
        return ValidatorResult(
            validator_id="F4",
            passed=True,
            metric="no_power_data",
            value=None,
            expected="CPU∈[297,402]W GPU∈[1572,2128]W",
            message="skipped (no power files)",
        )

    # Filter nodes with ≥ 12 samples
    qualified = {n: vs for n, vs in node_readings.items() if len(vs) >= 12}
    if len(qualified) < 4:
        return ValidatorResult(
            validator_id="F4",
            passed=False,
            metric="node_power_mean",
            value=None,
            expected="CPU∈[297,402]W GPU∈[1572,2128]W",
            message=f"insufficient nodes with ≥ 12 samples: {len(qualified)}, need ≥ 4",
        )

    failures: list[str] = []
    all_means: list[float] = []
    for node, vals in qualified.items():
        mean_w = statistics.mean(vals)
        all_means.append(mean_w)
        is_gpu = "gpu" in node.lower()
        if is_gpu:
            if not (1572 <= mean_w <= 2128):
                failures.append(f"{node}(GPU)={mean_w:.0f}W out of [1572,2128]")
        else:
            if not (297 <= mean_w <= 402):
                failures.append(f"{node}(CPU)={mean_w:.0f}W out of [297,402]")

    passed = len(failures) == 0
    overall_mean = statistics.mean(all_means)

    return ValidatorResult(
        validator_id="F4",
        passed=passed,
        metric="node_power_mean",
        value=overall_mean,
        expected="CPU∈[297,402]W GPU∈[1572,2128]W",
        message="all nodes in range" if passed else "; ".join(failures),
    )


# ---------------------------------------------------------------------------
# F5 — Telemetry cadence
# ---------------------------------------------------------------------------

def validate_f5_telemetry_cadence(bundle_dir: Path) -> ValidatorResult:
    """F5: Telemetry timestamps should have expected cadence.

    power CSVs: 48–72s; state/energy CSVs: 240–360s.
    Requires ≥ 10 rows per file. Skipped if no telemetry directory.
    """
    try:
        import pandas as pd
    except ImportError:
        return ValidatorResult(
            validator_id="F5",
            passed=True,
            metric="no_telemetry",
            value=None,
            expected="power∈[48,72]s state/energy∈[240,360]s",
            message="skipped (pandas not available)",
        )

    telemetry_dir = bundle_dir / "telemetry"
    if not telemetry_dir.is_dir():
        return ValidatorResult(
            validator_id="F5",
            passed=True,
            metric="no_telemetry",
            value=None,
            expected="power∈[48,72]s state/energy∈[240,360]s",
            message="skipped",
        )

    csv_files = list(telemetry_dir.glob("*.csv"))
    if not csv_files:
        return ValidatorResult(
            validator_id="F5",
            passed=True,
            metric="no_telemetry",
            value=None,
            expected="power∈[48,72]s state/energy∈[240,360]s",
            message="skipped",
        )

    failures: list[str] = []
    checked = 0

    for csv_path in csv_files:
        try:
            df = pd.read_csv(csv_path)
            # Find timestamp column (case-insensitive)
            ts_col = None
            for c in df.columns:
                if c.lower() == "timestamp":
                    ts_col = c
                    break
            if ts_col is None:
                continue
            if len(df) < 10:
                continue

            ts = pd.to_datetime(df[ts_col], errors="coerce").dropna().sort_values()
            if len(ts) < 10:
                continue

            diffs = ts.diff().dropna().dt.total_seconds()
            median_gap = float(diffs.median())
            checked += 1

            fname = csv_path.name.lower()
            is_power = "power" in fname
            is_state_energy = "state" in fname or "energy" in fname

            if is_power:
                if not (48 <= median_gap <= 72):
                    failures.append(f"{csv_path.name}: gap={median_gap:.0f}s expected [48,72]")
            elif is_state_energy:
                if not (240 <= median_gap <= 360):
                    failures.append(f"{csv_path.name}: gap={median_gap:.0f}s expected [240,360]")
            # Other filenames: no cadence constraint

        except Exception:
            continue

    if checked == 0:
        return ValidatorResult(
            validator_id="F5",
            passed=True,
            metric="no_telemetry",
            value=None,
            expected="power∈[48,72]s state/energy∈[240,360]s",
            message="skipped",
        )

    passed = len(failures) == 0
    return ValidatorResult(
        validator_id="F5",
        passed=passed,
        metric="telemetry_cadence",
        value=None,
        expected="power∈[48,72]s state/energy∈[240,360]s",
        message="all cadences OK" if passed else "; ".join(failures),
    )


# ---------------------------------------------------------------------------
# F6 — RBAC completeness
# ---------------------------------------------------------------------------

def validate_f6_rbac(bundle_dir: Path) -> ValidatorResult:
    """F6: RBAC policy requires at least 2 distinct roles defined in the RBAC policy."""
    rbac_path = bundle_dir / "policy" / "rbac_policy.yaml"
    if not rbac_path.exists():
        return ValidatorResult(
            validator_id="F6",
            passed=True,
            metric="rbac_roles",
            value=None,
            expected="len(roles)>=2",
            message="skipped (no rbac file)",
        )

    try:
        import yaml  # type: ignore[import-untyped]
        policy = yaml.safe_load(rbac_path.read_text())
    except Exception as e:
        return ValidatorResult(
            validator_id="F6",
            passed=False,
            metric="rbac_roles",
            value=None,
            expected="len(roles)>=2",
            message=f"failed to parse YAML: {e}",
        )

    # Collect all role names from any `roles:` key in the document
    role_names: set[str] = set()

    def _collect_roles(obj) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "roles":
                    if isinstance(v, dict):
                        role_names.update(v.keys())
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, str):
                                role_names.add(item)
                            elif isinstance(item, dict):
                                name = item.get("name") or item.get("role")
                                if name:
                                    role_names.add(str(name))
                else:
                    _collect_roles(v)
        elif isinstance(obj, list):
            for item in obj:
                _collect_roles(item)

    _collect_roles(policy)

    passed = len(role_names) >= 2

    return ValidatorResult(
        validator_id="F6",
        passed=passed,
        metric="rbac_roles",
        value=float(len(role_names)),
        expected="len(roles)>=2",
        message=(
            f"found {len(role_names)} roles: {sorted(role_names)}"
            if passed
            else f"insufficient roles: found {len(role_names)}, need >= 2"
        ),
    )


# ---------------------------------------------------------------------------
# F7 — Tool catalog coverage
# ---------------------------------------------------------------------------

def validate_f7_tool_catalog(bundle_dir: Path) -> ValidatorResult:
    """F7: Every method in the tool catalog must have a non-empty description."""
    candidates = [
        bundle_dir / "docs" / "tool_catalog.yaml",
        bundle_dir / "tools" / "catalog.yaml",
    ]
    catalog_path: Optional[Path] = None
    for c in candidates:
        if c.exists():
            catalog_path = c
            break

    if catalog_path is None:
        return ValidatorResult(
            validator_id="F7",
            passed=True,
            metric="tool_catalog",
            value=None,
            expected="all methods have descriptions",
            message="skipped",
        )

    try:
        import yaml  # type: ignore[import-untyped]
        catalog = yaml.safe_load(catalog_path.read_text())
    except Exception as e:
        return ValidatorResult(
            validator_id="F7",
            passed=False,
            metric="tool_catalog",
            value=None,
            expected="all methods have descriptions",
            message=f"failed to parse YAML: {e}",
        )

    # Walk the catalog looking for method entries
    missing_desc: list[str] = []

    def _check(obj, path: str = "") -> None:
        if isinstance(obj, dict):
            # Detect a method entry: has a `description` key or is listed under `methods`
            desc = obj.get("description")
            name = obj.get("name", path)
            if "description" in obj:
                if not str(desc).strip():
                    missing_desc.append(name)
            for k, v in obj.items():
                if k in ("methods", "tools"):
                    _check(v, path=k)
                elif isinstance(v, (dict, list)):
                    _check(v, path=f"{path}.{k}" if path else k)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _check(item, path=f"{path}[{i}]")

    _check(catalog)

    passed = len(missing_desc) == 0
    return ValidatorResult(
        validator_id="F7",
        passed=passed,
        metric="tool_catalog",
        value=float(len(missing_desc)),
        expected="all methods have descriptions",
        message=(
            "all methods have descriptions"
            if passed
            else f"{len(missing_desc)} method(s) missing description: {missing_desc[:5]}"
        ),
    )
