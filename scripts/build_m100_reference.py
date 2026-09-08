#!/usr/bin/env python3
"""Phase 0 — build the M100 reference substrate from the real ExaData sample.

Reads the single real Marconi100 node sample bundled in the ExaData repo
(``examples/anomaly_detection/388.parquet`` — a 15-min node-aggregated, wide-format
table of IPMI metrics) plus the metric→plugin catalog (``M100_metrics.csv``), and
emits two committed artifacts under ``benchmark/environments/_m100_reference/``:

    metric_distributions.json   per-metric robust distribution parameters + plugin + unit
    metric_map.md               human-readable M100 metric → canonical mapping table

These artifacts let ``scripts/build_m100_bundles.py`` synthesise M100-faithful
telemetry **offline** (without the 30 MB parquet or the 265 GB full dataset),
while keeping the statistical grounding auditable.

The wide sample stores ``{metric}_avg/_std/_min/_max`` columns per 15-min window.
For each metric we derive:

    mean              = median over time of the per-window average  (robust baseline)
    within_window_std = median of the per-window std                (real fast noise)
    across_window_std = std over time of the per-window average      (real slow drift)
    lo / hi           = 1st pct of _min / 99th pct of _max           (clamp bounds)

Usage::

    uv run python scripts/build_m100_reference.py \
        [--sample $EXADATA_DIR/examples/anomaly_detection/388.parquet] \
        [--catalog $EXADATA_DIR/data_extraction/M100_metrics.csv] \
        [--out benchmark/environments/_m100_reference]

Provenance: CINECA Marconi100 ExaData dataset, doi:10.1038/s41597-023-02174-3.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path

import pandas as pd

# Repo-relative defaults. The exadata dataset repo is a sibling of the aobench repo.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_SAMPLE = _REPO_ROOT / ".." / "exadata" / "examples" / "anomaly_detection" / "388.parquet"
_DEFAULT_CATALOG = _REPO_ROOT / ".." / "exadata" / "data_extraction" / "M100_metrics.csv"
_DEFAULT_OUT = _REPO_ROOT / "benchmark" / "environments" / "_m100_reference"

_AGG_SUFFIXES = ("_avg", "_std", "_min", "_max")


def infer_unit(metric: str) -> str:
    """Infer the physical unit of an IPMI metric from its name (per ipmi.md)."""
    m = metric.lower()
    if m == "total_power" or m.endswith("_power") or m == "fan_disk_power":
        return "W"
    if m.endswith("_temp") or m in {"ambient", "pcie"}:
        return "°C"
    if m.startswith(("fan0", "fan1", "fan2", "fan3")):
        return "RPM"
    if m.endswith(("input_voltag", "output_volta")):
        return "V"
    if m.endswith("output_curre"):
        return "A"
    if m.startswith("gv100card"):
        return "W"  # GV100 (Volta) GPU board power
    return ""


def load_plugin_map(catalog_path: Path) -> dict[str, str]:
    """Map each metric name to its M100 plugin (e.g. ipmi_pub) from M100_metrics.csv."""
    mapping: dict[str, str] = {}
    if not catalog_path.exists():
        return mapping
    with catalog_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            metric = (row.get("metric") or "").strip()
            plugin = (row.get("plugin") or "").strip()
            if metric:
                mapping[metric] = plugin
    return mapping


def metric_prefixes(columns: list[str]) -> list[str]:
    """Return the sorted set of metric prefixes from wide ``{metric}_{agg}`` columns."""
    prefixes = set()
    for c in columns:
        for suf in _AGG_SUFFIXES:
            if c.endswith(suf):
                prefixes.add(c[: -len(suf)])
                break
    return sorted(prefixes)


def build_distributions(sample_path: Path, plugin_map: dict[str, str]) -> dict[str, dict]:
    """Fit robust per-metric distribution parameters from the wide sample parquet."""
    df = pd.read_parquet(sample_path)
    dists: dict[str, dict] = {}
    for metric in metric_prefixes(list(df.columns)):
        avg, std = f"{metric}_avg", f"{metric}_std"
        lo_c, hi_c = f"{metric}_min", f"{metric}_max"
        if avg not in df.columns:
            continue
        avg_series = df[avg].dropna()
        if avg_series.empty:
            continue
        mean = float(avg_series.median())
        within = float(df[std].dropna().median()) if std in df.columns else 0.0
        across = float(avg_series.std())
        lo = float(df[lo_c].dropna().quantile(0.01)) if lo_c in df.columns else mean
        hi = float(df[hi_c].dropna().quantile(0.99)) if hi_c in df.columns else mean
        dists[metric] = {
            "plugin": plugin_map.get(metric, "ipmi_pub"),
            "unit": infer_unit(metric),
            "mean": round(mean, 4),
            "within_window_std": round(within, 4),
            "across_window_std": round(across, 4),
            "lo": round(lo, 4),
            "hi": round(hi, 4),
        }
    return dists


def build_distributions_from_dir(
    aggregated_dir: Path, plugin_map: dict[str, str], n_nodes: int, seed: int,
) -> tuple[dict[str, dict], int]:
    """Fit per-metric distributions from a POPULATION of real node parquets.

    ``time_aggregated/`` holds one wide ``{node}.parquet`` per real M100 node (same
    354-column format as the single sample). We sample ``n_nodes`` nodes and aggregate
    robust per-metric statistics across the population, additionally capturing
    ``node_baseline_std`` — the spread of per-node baselines — so synthesised env nodes
    can be given genuinely heterogeneous real baselines.

    Returns (distributions, n_nodes_used).
    """
    import random

    files = sorted(aggregated_dir.glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No node parquets found in {aggregated_dir}")
    rng = random.Random(seed)
    if len(files) > n_nodes:
        files = sorted(rng.sample(files, n_nodes))

    # Per-metric accumulators across nodes.
    node_means: dict[str, list[float]] = {}
    node_within: dict[str, list[float]] = {}
    node_across: dict[str, list[float]] = {}
    node_lo: dict[str, list[float]] = {}
    node_hi: dict[str, list[float]] = {}

    used = 0
    for fp in files:
        try:
            df = pd.read_parquet(fp)
        except (OSError, ValueError):
            # Skip any unreadable node: pyarrow raises ArrowInvalid (a ValueError)
            # for a corrupt file and ArrowIOError (an OSError) for an absent one.
            continue
        used += 1
        for metric in metric_prefixes(list(df.columns)):
            avg = f"{metric}_avg"
            if avg not in df.columns:
                continue
            avg_series = df[avg].dropna()
            if avg_series.empty:
                continue
            node_means.setdefault(metric, []).append(float(avg_series.median()))
            std_c = f"{metric}_std"
            if std_c in df.columns and not df[std_c].dropna().empty:
                node_within.setdefault(metric, []).append(float(df[std_c].dropna().median()))
            node_across.setdefault(metric, []).append(float(avg_series.std()))
            lo_c, hi_c = f"{metric}_min", f"{metric}_max"
            if lo_c in df.columns and not df[lo_c].dropna().empty:
                node_lo.setdefault(metric, []).append(float(df[lo_c].dropna().quantile(0.01)))
            if hi_c in df.columns and not df[hi_c].dropna().empty:
                node_hi.setdefault(metric, []).append(float(df[hi_c].dropna().quantile(0.99)))

    def _finite(xs: list[float]) -> list[float]:
        return [x for x in xs if math.isfinite(x)]

    def _median(xs: list[float]) -> float:
        xs = _finite(xs)
        return float(statistics.median(xs)) if xs else 0.0

    dists: dict[str, dict] = {}
    for metric, raw_means in node_means.items():
        means = _finite(raw_means)
        if not means:
            continue
        node_std = float(statistics.pstdev(means)) if len(means) > 1 else 0.0
        dists[metric] = {
            "plugin": plugin_map.get(metric, "ipmi_pub"),
            "unit": infer_unit(metric),
            "mean": round(_median(means), 4),
            "within_window_std": round(_median(node_within.get(metric, [])), 4),
            "across_window_std": round(_median(node_across.get(metric, [])), 4),
            "node_baseline_std": round(node_std, 4),
            "lo": round(min(_finite(node_lo.get(metric, [])) or [min(means)]), 4),
            "hi": round(max(_finite(node_hi.get(metric, [])) or [max(means)]), 4),
            "n_nodes": len(means),
        }
    return dists, used


# Units for known non-IPMI metrics (the long-format path can't infer these).
_LONG_UNITS = {
    "mem_free": "KB", "mem_total": "KB", "mem_cached": "KB", "mem_buffers": "KB",
    "swap_free": "KB", "swap_total": "KB",
    "cpu_user": "%", "cpu_system": "%", "cpu_idle": "%", "cpu_wio": "%",
    "load_one": "", "load_five": "", "load_fifteen": "",
    "bytes_in": "bytes/s", "bytes_out": "bytes/s",
    "Supply_Air_Temperature": "°C", "Return_Air_Temperature": "°C", "Fan_Speed": "%",
    "state": "",
}
# Plugin for known non-IPMI metrics (overrides --long-plugin per metric).
_LONG_PLUGINS = {
    "Supply_Air_Temperature": "vertiv_pub", "Return_Air_Temperature": "vertiv_pub",
    "Fan_Speed": "vertiv_pub", "state": "nagios_pub",
}


def build_distributions_from_long(
    long_dir: Path, plugin: str, seed: int,
) -> dict[str, dict]:
    """Fit per-metric distributions from long-format ``metric=<m>/a_0.parquet`` files.

    Each file has columns ``timestamp, value, node``. Stats are aggregated per node then
    across nodes (mirrors the population fit), capturing ``node_baseline_std``.
    """
    files = sorted(long_dir.glob("**/a_0.parquet"))
    dists: dict[str, dict] = {}
    for fp in files:
        # metric name from the .../metric=<name>/a_0.parquet path
        metric = None
        for part in fp.parts:
            if part.startswith("metric="):
                metric = part.split("=", 1)[1]
        if metric is None:
            continue
        # Pick a grouping column: compute node where present, else facility device.
        import pyarrow.parquet as pq
        schema_names = set(pq.ParquetFile(fp).schema_arrow.names)
        group_col = next((c for c in ("node", "device") if c in schema_names), None)
        read_cols = ["value"] + ([group_col] if group_col else [])
        df = pd.read_parquet(fp, columns=read_cols).dropna()
        if df.empty:
            continue
        # Cap rows for tractability; deterministic.
        if len(df) > 4_000_000:
            df = df.sample(n=4_000_000, random_state=seed)
        if group_col is None:
            # No spatial grouping → single population.
            df = df.assign(_g=0)
            group_col = "_g"
        per_node = df.groupby(group_col)["value"]
        node_medians = per_node.median().dropna()
        node_stds = per_node.std().dropna()
        if node_medians.empty:
            continue
        mean = float(node_medians.median())
        within = float(node_stds.median()) if not node_stds.empty else 0.0
        node_std = float(node_medians.std()) if len(node_medians) > 1 else 0.0
        lo = float(df["value"].quantile(0.01))
        hi = float(df["value"].quantile(0.99))
        dists[metric] = {
            "plugin": _LONG_PLUGINS.get(metric, plugin),
            "unit": _LONG_UNITS.get(metric, ""),
            "mean": round(mean, 4),
            "within_window_std": round(within, 4),
            "across_window_std": round(within, 4),
            "node_baseline_std": round(node_std, 4),
            "lo": round(lo, 4),
            "hi": round(hi, 4),
            "n_nodes": len(node_medians),
        }
    return dists


def write_metric_map(out_dir: Path, dists: dict[str, dict], sample_path: Path) -> None:
    """Write the human-readable M100 metric → canonical mapping table."""
    lines = [
        "# M100 ExaData → AOBench canonical metric map",
        "",
        "Generated by `scripts/build_m100_reference.py` from the real Marconi100",
        (
            f"node sample `{sample_path.name}` drawn from the public CINECA Marconi100 "
            "ExaData dataset (doi:10.1038/s41597-023-02174-3)."
        ),
        "",
        "AOBench stores telemetry in long format with canonical columns",
        "`timestamp, node_id, metric_name, value, unit` plus an extra `plugin` column.",
        "M100 metric names are used verbatim as `metric_name`; the node sample covers the",
        "`ipmi_pub` plugin. Distribution parameters are robust fits over the real time series.",
        "",
        "| `metric_name` | plugin | unit | baseline mean | clamp [lo, hi] |",
        "|---|---|---|---|---|",
    ]
    for metric in sorted(dists):
        d = dists[metric]
        lines.append(
            f"| `{metric}` | {d['plugin']} | {d['unit'] or '—'} | "
            f"{d['mean']:g} | [{d['lo']:g}, {d['hi']:g}] |"
        )
    lines.append("")
    (out_dir / "metric_map.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the M100 reference substrate")
    parser.add_argument("--sample", type=Path, default=_DEFAULT_SAMPLE)
    parser.add_argument("--catalog", type=Path, default=_DEFAULT_CATALOG)
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT)
    parser.add_argument(
        "--aggregated-dir", type=Path, default=None,
        help="Directory of per-node wide parquets (time_aggregated/). When set, fit "
             "distributions from a POPULATION of real nodes instead of the single sample.",
    )
    parser.add_argument("--n-nodes", type=int, default=120,
                        help="Number of real nodes to sample in --aggregated-dir mode.")
    parser.add_argument("--seed", type=int, default=388,
                        help="Deterministic node-sampling seed for --aggregated-dir mode.")
    parser.add_argument("--long-metrics-dir", type=Path, default=None,
                        help="Directory of long-format metric=<m>/a_0.parquet files (e.g. "
                             "extracted ganglia_pub metrics). Fits and (with --merge-into) "
                             "appends them to an existing reference JSON.")
    parser.add_argument("--long-plugin", default="ganglia_pub",
                        help="Plugin label for --long-metrics-dir metrics.")
    parser.add_argument("--merge-into", type=Path, default=None,
                        help="Existing metric_distributions.json to extend with newly fit metrics.")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    plugin_map = load_plugin_map(args.catalog)

    if args.long_metrics_dir is not None:
        new_metrics = build_distributions_from_long(
            args.long_metrics_dir, args.long_plugin, args.seed,
        )
        base = json.loads(args.merge_into.read_text(encoding="utf-8")) if args.merge_into else {
            "source": "CINECA Marconi100 ExaData", "sample_file": "long-format fit",
            "cadence_seconds": 900, "note": "long-format metrics", "metrics": {},
        }
        base["metrics"].update(new_metrics)
        out_json = args.out / "metric_distributions.json"
        out_json.write_text(json.dumps(base, indent=2), encoding="utf-8")
        write_metric_map(args.out, base["metrics"], Path(base.get("sample_file", "merged")))
        print(f"Added {len(new_metrics)} {args.long_plugin} metrics "
              f"({sorted(new_metrics)}) → {out_json} (total {len(base['metrics'])})")
        return

    if args.aggregated_dir is not None:
        dists, used = build_distributions_from_dir(
            args.aggregated_dir, plugin_map, args.n_nodes, args.seed,
        )
        source_label = f"time_aggregated population ({used} nodes, seed={args.seed})"
        note = (
            "Per-metric distributions fit across a POPULATION of real M100 nodes. "
            "mean=median over nodes of per-node median(_avg); within_window_std=median "
            "over nodes of median(_std); across_window_std=median over nodes of std(_avg); "
            "node_baseline_std=spread of per-node baselines (for heterogeneous env nodes); "
            "lo/hi=population envelope of 1st/99th pct of _min/_max."
        )
    else:
        if not args.sample.exists():
            raise FileNotFoundError(
                f"M100 sample parquet not found: {args.sample}\n"
                "Expected the ExaData repo as a sibling of aobench/. "
                "Pass --sample to point at examples/anomaly_detection/388.parquet, "
                "or --aggregated-dir for the full time_aggregated/ population."
            )
        dists = build_distributions(args.sample, plugin_map)
        source_label = args.sample.name
        note = (
            "Robust per-metric distribution parameters fit from the real node-aggregated "
            "IPMI sample. mean=median(_avg), within_window_std=median(_std), "
            "across_window_std=std(_avg), lo/hi=1st/99th pct of _min/_max."
        )

    payload = {
        "source": "CINECA Marconi100 ExaData",
        "sample_file": source_label,
        "cadence_seconds": 900,
        "note": note,
        "metrics": dists,
    }
    out_json = args.out / "metric_distributions.json"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_metric_map(args.out, dists, Path(source_label))

    print(f"Wrote {len(dists)} metric distributions ({source_label}) → {out_json}")
    print(f"Wrote metric map → {args.out / 'metric_map.md'}")


if __name__ == "__main__":
    main()
