"""BenchmarkService — transport-agnostic façade over the benchmark engine.

Implements spec-0001 / ADR 0001. Every surface (CLI, REST, MCP, A2A) calls this
so run+score logic lives in exactly one place and CLEAR scores never diverge.
Contains no transport and no scoring logic — it orchestrates existing components
(loaders, BenchmarkRunner, AggregateScorer) and returns Pydantic models.
"""

from __future__ import annotations

import hashlib
import os
import statistics
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from aobench.schemas.result import BenchmarkResult
from aobench.schemas.trace import Trace
from aobench.service.errors import (
    AdapterError,
    EnvNotFound,
    RunNotFound,
    SplitLockedError,
    TaskNotFound,
)
from aobench.service.jobs import InMemoryJobRegistry, JobRecord, JobResult, run_job
from aobench.service.models import (
    CompareResult,
    DatasetInfo,
    EnvSummary,
    Fingerprint,
    ReportModel,
    RobustnessResult,
    RunHandle,
    RunRecord,
    TaskSummary,
)
from aobench.utils.ids import make_run_id

if TYPE_CHECKING:
    from aobench.adapters.base import BaseAdapter
    from aobench.exporters.base_exporter import BaseExporter


def resolve_adapter(name: str) -> "BaseAdapter":
    """Resolve an adapter string to an adapter instance (mirrors the CLI registry).

    Accepts: ``direct_qa``, ``openai[:model]``, ``anthropic[:model]``,
    ``mcp:stdio:CMD`` / ``mcp:sse:URL``. Raises :class:`AdapterError` on unknown
    prefixes so transports can map it to a client error.
    """
    from aobench.adapters.direct_qa_adapter import DirectQAAdapter

    prefix = name.split(":", 1)[0]
    try:
        if prefix == "direct_qa":
            return DirectQAAdapter()
        if prefix == "openai":
            from aobench.adapters.openai_adapter import OpenAIAdapter

            model = name.split(":", 1)[1] if ":" in name else "gpt-4o"
            return OpenAIAdapter(model=model)
        if prefix == "anthropic":
            from aobench.adapters.anthropic_adapter import AnthropicAdapter

            model = name.split(":", 1)[1] if ":" in name else "claude-sonnet-4-6"
            return AnthropicAdapter(model=model)
        if prefix == "mcp":
            from aobench.adapters.mcp_client_adapter import MCPClientAdapter

            server_spec = name[len("mcp:") :] if ":" in name else ""
            return MCPClientAdapter(server=server_spec)
    except Exception as exc:  # noqa: BLE001 — surface any construction failure uniformly
        raise AdapterError(f"failed to build adapter {name!r}: {exc}") from exc

    raise AdapterError(
        f"unknown adapter {name!r}; known prefixes: direct_qa, openai, anthropic, mcp"
    )


class BenchmarkService:
    """Single entry point to run, score, and inspect benchmarks."""

    def __init__(
        self,
        benchmark_root: str | Path = "benchmark",
        output_root: str | Path = "data/runs",
    ) -> None:
        # The sentinel default "benchmark" means "auto-detect": prefer
        # $AOBENCH_BENCHMARK_ROOT, then a checkout found from the CWD, then the
        # copy bundled inside an installed wheel. An explicit path is honored
        # as-is (failures stay lazy, as before). See aobench.paths.
        from aobench.paths import default_benchmark_root

        if benchmark_root is None or str(benchmark_root) == "benchmark":
            resolved = default_benchmark_root()
            self._benchmark_root = resolved if resolved is not None else Path("benchmark")
        else:
            self._benchmark_root = Path(benchmark_root)
        self._output_root = Path(output_root)
        self._jobs = InMemoryJobRegistry()
        self._job_counter = 0

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _task_path(self, task_id: str) -> Path:
        return self._benchmark_root / "tasks" / "specs" / f"{task_id}.json"

    def _env_path(self, env_id: str) -> Path:
        return self._benchmark_root / "environments" / env_id

    def _require_task(self, task_id: str) -> Path:
        p = self._task_path(task_id)
        if not p.exists():
            raise TaskNotFound(task_id)
        return p

    def _require_env(self, env_id: str) -> Path:
        p = self._env_path(env_id)
        if not p.is_dir():
            raise EnvNotFound(env_id)
        return p

    def _env_manifest_sha256(self, env_id: str) -> Optional[str]:
        manifest = self._env_path(env_id) / "manifest.txt"
        if not manifest.exists():
            return None
        return hashlib.sha256(manifest.read_bytes()).hexdigest()

    @staticmethod
    def _check_split(split: str) -> None:
        if split == "test" and not os.environ.get("AOBENCH_UNLOCK_TEST"):
            raise SplitLockedError(
                "the 'test' split is locked; set AOBENCH_UNLOCK_TEST=1 to unlock "
                "(one-shot only)"
            )

    def _fingerprint(self, env_id: str, adapter_obj: "BaseAdapter", adapter_name: str,
                     seed: Optional[int], replay: str) -> Fingerprint:
        return Fingerprint(
            env_manifest_sha256=self._env_manifest_sha256(env_id),
            model_snapshot=getattr(adapter_obj, "model", None) or adapter_name,
            adapter=adapter_name,
            seed=seed,
            replay=replay,
        )

    # ------------------------------------------------------------------ #
    # Run + score
    # ------------------------------------------------------------------ #
    def submit_run(
        self,
        task_id: str,
        env_id: str,
        adapter: str = "direct_qa",
        *,
        role: Optional[str] = None,  # reserved: transports map identity→role (RBAC in engine)
        split: str = "dev",
        seed: Optional[int] = None,
        replay: str = "live",
        exporter: "BaseExporter | None" = None,
    ) -> RunHandle:
        """Run one task synchronously and return a completed RunHandle.

        The async path (ADR 0002) reuses this same method inside a worker and
        returns status='queued' from the enqueuing layer.
        """
        self._check_split(split)
        self._require_task(task_id)
        self._require_env(env_id)

        adapter_obj = resolve_adapter(adapter)

        from aobench.runners.runner import BenchmarkRunner

        run_id = make_run_id()
        runner = BenchmarkRunner(
            adapter=adapter_obj,
            benchmark_root=self._benchmark_root,
            output_root=self._output_root,
            exporter=exporter,
        )
        try:
            result = runner.run(task_id, env_id, run_id=run_id)
        except (TaskNotFound, EnvNotFound, SplitLockedError):
            raise
        except Exception as exc:  # noqa: BLE001
            raise AdapterError(f"run failed for {task_id}/{env_id}: {exc}") from exc

        return RunHandle(
            run_id=run_id,
            status="completed",
            aggregate_score=result.aggregate_score,
            fingerprint=self._fingerprint(env_id, adapter_obj, adapter, seed, replay),
        )

    def score_trace(self, task_id: str, trace: Trace, run_id: str = "adhoc") -> BenchmarkResult:
        """Score a supplied trace against a task without re-running the agent."""
        from aobench.loaders.task_loader import load_task
        from aobench.scorers.aggregate import AggregateScorer

        task = load_task(self._require_task(task_id))
        scorer = AggregateScorer(self._benchmark_root / "configs" / "scoring_profiles.yaml")
        return scorer.score(task, trace, run_id=run_id)

    # ------------------------------------------------------------------ #
    # Async submission (job registry; ADR 0002)
    # ------------------------------------------------------------------ #
    def enqueue_run(
        self,
        task_id: str,
        env_id: str,
        adapter: str = "direct_qa",
        *,
        role: Optional[str] = None,
        split: str = "dev",
        seed: Optional[int] = None,
        replay: str = "live",
    ) -> JobRecord:
        """Submit a run as a tracked job and return its record.

        Backed by the in-memory job registry, the run executes in-process here and
        the terminal state is queryable via :meth:`get_job`. A durable arq/Redis
        worker (ADR 0002) swaps in by running :func:`run_job` off-process instead;
        the registry interface and the returned record are identical either way.
        """
        self._job_counter += 1
        job_id = f"job_{self._job_counter:06d}"
        self._jobs.submit(task_id, env_id, adapter, job_id=job_id)

        def _do() -> JobResult:
            handle = self.submit_run(task_id, env_id, adapter, role=role,
                                     split=split, seed=seed, replay=replay)
            return JobResult(run_id=handle.run_id, aggregate_score=handle.aggregate_score)

        return run_job(self._jobs, job_id, _do)

    def get_job(self, job_id: str) -> JobRecord:
        rec = self._jobs.get(job_id)
        if rec is None:
            raise RunNotFound(f"job {job_id}")
        return rec

    def list_jobs(self) -> list[JobRecord]:
        return self._jobs.list()

    # ------------------------------------------------------------------ #
    # Read-back
    # ------------------------------------------------------------------ #
    def _run_dir(self, run_id: str) -> Path:
        d = self._output_root / run_id
        if not d.is_dir():
            raise RunNotFound(run_id)
        return d

    def get_run(self, run_id: str) -> RunRecord:
        d = self._run_dir(run_id)
        results: list[BenchmarkResult] = []
        results_dir = d / "results"
        if results_dir.is_dir():
            for f in sorted(results_dir.glob("*_result.json")):
                try:
                    results.append(BenchmarkResult.model_validate_json(f.read_text()))
                except Exception:  # noqa: BLE001 — skip unrelated artifacts
                    continue
        scores = [r.aggregate_score for r in results if r.aggregate_score is not None]
        return RunRecord(
            run_id=run_id,
            status="completed",
            n_tasks=len(results),
            aggregate_score=(statistics.fmean(scores) if scores else None),
            hard_fail_count=sum(1 for r in results if r.hard_fail),
            results=results,
        )

    def get_trace(self, run_id: str, task_id: Optional[str] = None) -> Trace:
        d = self._run_dir(run_id)
        traces_dir = d / "traces"
        candidates = sorted(traces_dir.glob("*_trace.json")) if traces_dir.is_dir() else []
        if task_id is not None:
            candidates = [c for c in candidates if c.name.startswith(f"{task_id}_")]
        if not candidates:
            raise RunNotFound(f"no trace for run {run_id}"
                              + (f" task {task_id}" if task_id else ""))
        return Trace.model_validate_json(candidates[0].read_text())

    def get_report(self, run_id: str, fmt: str = "json") -> ReportModel:
        d = self._run_dir(run_id)
        from aobench.reports.json_report import build_run_summary

        summary = build_run_summary(d)
        if fmt in ("json", "summary", "clear"):
            # 'clear' is served from the same persisted summary (which carries the
            # CLEAR-relevant aggregates); a dedicated clear renderer is spec-0002.
            return ReportModel(run_id=run_id, format=fmt, payload=summary)
        raise ValueError(f"unsupported report format {fmt!r}")

    # ------------------------------------------------------------------ #
    # Catalog
    # ------------------------------------------------------------------ #
    def list_tasks(
        self,
        split: Optional[str] = None,
        qcat: Optional[str] = None,
        role: Optional[str] = None,
    ) -> list[TaskSummary]:
        from aobench.loaders.task_loader import load_tasks_from_dir

        specs_dir = self._benchmark_root / "tasks" / "specs"
        out: list[TaskSummary] = []
        for t in load_tasks_from_dir(specs_dir):
            t_qcat = getattr(t, "category", None) or getattr(t, "qcat", None)
            t_role = getattr(t, "role", None)
            if qcat is not None and t_qcat != qcat:
                continue
            if role is not None and t_role != role:
                continue
            hsc = getattr(t, "hybrid_scoring", None)
            scoring_mode = getattr(hsc, "scoring_mode", None) if hsc else None
            out.append(
                TaskSummary(
                    task_id=t.task_id,
                    qcat=t_qcat,
                    role=t_role,
                    environment_id=getattr(t, "environment_id", None),
                    scoring_mode=scoring_mode,
                    difficulty_tier=getattr(t, "difficulty_tier", None),
                )
            )
        return out

    def list_datasets(self) -> list[DatasetInfo]:
        """Report the versioned task corpus and per-split task counts (Feature 5)."""
        from aobench.benchmark.tasks.dataset_splits import (
            LITE_TASK_IDS,
            SPLIT_FROZEN_CORPUS_VERSION,
            SPLIT_FROZEN_DATE,
            TEST_TASK_IDS,
        )

        all_ids = {t.task_id for t in self.list_tasks()}
        test = set(TEST_TASK_IDS) & all_ids
        lite = set(LITE_TASK_IDS) & all_ids
        split_counts = {
            "all": len(all_ids),
            "dev": len(all_ids - test),
            "test": len(test),
            "lite": len(lite),
        }
        return [
            DatasetInfo(
                dataset_version=SPLIT_FROZEN_CORPUS_VERSION,
                frozen_date=SPLIT_FROZEN_DATE,
                n_tasks=len(all_ids),
                split_counts=split_counts,
            )
        ]

    def list_envs(self) -> list[EnvSummary]:
        envs_dir = self._benchmark_root / "environments"
        out: list[EnvSummary] = []
        if not envs_dir.is_dir():
            return out
        for d in sorted(envs_dir.iterdir()):
            if not d.is_dir() or d.name.startswith("_"):
                continue
            manifest = d / "manifest.txt"
            n_files = None
            if manifest.exists():
                n_files = sum(1 for _ in manifest.read_text().splitlines() if _.strip())
            out.append(
                EnvSummary(
                    env_id=d.name,
                    manifest_sha256=self._env_manifest_sha256(d.name),
                    n_files=n_files,
                )
            )
        return out

    # ------------------------------------------------------------------ #
    # Compare + robustness
    # ------------------------------------------------------------------ #
    def compare(self, run_a: str, run_b: str) -> CompareResult:
        ra, rb = self.get_run(run_a), self.get_run(run_b)

        def _dim_mean(rec: RunRecord, dim: str) -> Optional[float]:
            vals = [
                getattr(r.dimension_scores, dim)
                for r in rec.results
                if getattr(r.dimension_scores, dim, None) is not None
            ]
            return statistics.fmean(vals) if vals else None

        dims = ["outcome", "tool_use", "grounding", "governance", "robustness", "efficiency"]
        per_dim: dict[str, Optional[float]] = {}
        for dim in dims:
            a, b = _dim_mean(ra, dim), _dim_mean(rb, dim)
            per_dim[dim] = (b - a) if (a is not None and b is not None) else None

        delta = (
            rb.aggregate_score - ra.aggregate_score
            if (ra.aggregate_score is not None and rb.aggregate_score is not None)
            else None
        )
        return CompareResult(
            run_a=run_a,
            run_b=run_b,
            aggregate_a=ra.aggregate_score,
            aggregate_b=rb.aggregate_score,
            delta=delta,
            per_dimension_delta=per_dim,
        )

    def robustness(
        self,
        task_id: str,
        env_id: str,
        adapter: str,
        n: int,
        *,
        pass_threshold: float = 0.5,
        k: int = 2,
    ) -> RobustnessResult:
        from aobench.analysis.rigor import summarize_scores

        scores: list[Optional[float]] = []
        run_ids: list[str] = []
        for _ in range(max(1, n)):
            h = self.submit_run(task_id, env_id, adapter, split="dev")
            scores.append(h.aggregate_score)
            run_ids.append(h.run_id)
        present = [s for s in scores if s is not None]
        rigor = summarize_scores(present, threshold=pass_threshold, k=min(k, max(1, len(present))))
        return RobustnessResult(
            task_id=task_id,
            env_id=env_id,
            adapter=adapter,
            n=n,
            scores=scores,
            mean=rigor.mean,
            stdev=rigor.stdev,
            run_ids=run_ids,
            pass_threshold=pass_threshold,
            pass_1=rigor.pass_1,
            pass_k=rigor.pass_k,
            k=rigor.k,
            ci_low=rigor.ci_low,
            ci_high=rigor.ci_high,
        )
