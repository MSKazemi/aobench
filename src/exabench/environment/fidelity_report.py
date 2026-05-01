"""FidelityReport: run F1–F7 validators and render results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from exabench.environment.fidelity_validators import (
    ValidatorResult,
    validate_f1_job_duration,
    validate_f2_job_size,
    validate_f3_job_state_mix,
    validate_f4_node_power,
    validate_f5_telemetry_cadence,
    validate_f6_rbac,
    validate_f7_tool_catalog,
)

_VALIDATORS = [
    validate_f1_job_duration,
    validate_f2_job_size,
    validate_f3_job_state_mix,
    validate_f4_node_power,
    validate_f5_telemetry_cadence,
    validate_f6_rbac,
    validate_f7_tool_catalog,
]


@dataclass
class FidelityReport:
    """Aggregated fidelity validation report for a single environment bundle."""

    env_id: str
    env_dir: Path
    results: list[ValidatorResult] = field(default_factory=list)
    generated_at: str = ""

    @property
    def passed(self) -> bool:
        """True if every validator passed (or was skipped)."""
        return all(r.passed for r in self.results)

    def run_all(self) -> "FidelityReport":
        """Run F1–F7 validators against env_dir. Populates results in-place."""
        self.results = []
        for fn in _VALIDATORS:
            try:
                self.results.append(fn(self.env_dir))
            except Exception as e:  # noqa: BLE001
                self.results.append(
                    ValidatorResult(
                        validator_id=fn.__name__,
                        passed=False,
                        metric="error",
                        value=None,
                        expected="",
                        message=f"Exception: {e}",
                    )
                )
        self.generated_at = datetime.now(tz=timezone.utc).isoformat()
        return self

    def to_markdown(self) -> str:
        """Render a human-readable Markdown report."""
        lines = [
            f"# Fidelity Report: {self.env_id}",
            f"Generated: {self.generated_at}",
            "",
        ]
        for r in self.results:
            status = "✓ PASS" if r.passed else "✗ FAIL"
            lines.append(f"## {r.validator_id} — {status}")
            lines.append(f"- Metric: {r.metric}")
            if r.value is not None:
                lines.append(f"- Value: {r.value:.4g}")
            lines.append(f"- Expected: {r.expected}")
            lines.append(f"- {r.message}")
            lines.append("")
        overall = "PASS" if self.passed else "FAIL"
        lines.append(f"**Overall: {overall}**")
        return "\n".join(lines)
