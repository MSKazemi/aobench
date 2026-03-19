"""Unit tests for LangfuseExporter."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from exabench.schemas.result import BenchmarkResult, DimensionScores
from exabench.schemas.task import TaskSpec
from exabench.schemas.trace import Observation, Trace, TraceStep, ToolCall


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_task() -> TaskSpec:
    return TaskSpec(
        task_id="JOB_USR_001",
        title="Test task",
        query_text="What is the status of job 123?",
        role="scientific_user",
        qcat="JOB",
        difficulty="easy",
        environment_id="env_01",
        expected_answer_type="lookup",
    )


def _make_trace() -> Trace:
    return Trace(
        trace_id="trace-abc",
        run_id="run-xyz",
        task_id="JOB_USR_001",
        role="scientific_user",
        environment_id="env_01",
        adapter_name="direct_qa",
        model_name="gpt-4o",
        steps=[
            TraceStep(
                step_id=0,
                reasoning="I need to check the job status.",
                tool_call=ToolCall(tool_name="slurm", arguments={"method": "job_details", "job_id": "123"}),
                observation=Observation(content={"state": "RUNNING"}),
                timestamp=datetime(2026, 3, 19, 10, 0, 0, tzinfo=timezone.utc),
            ),
            TraceStep(
                step_id=1,
                reasoning="Job is running.",
                timestamp=datetime(2026, 3, 19, 10, 0, 1, tzinfo=timezone.utc),
            ),
        ],
        final_answer="Job 123 is currently RUNNING.",
        start_time=datetime(2026, 3, 19, 10, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 3, 19, 10, 0, 5, tzinfo=timezone.utc),
        total_tokens=200,
        prompt_tokens=150,
        completion_tokens=50,
    )


def _make_result() -> BenchmarkResult:
    return BenchmarkResult(
        result_id="result-001",
        run_id="run-xyz",
        task_id="JOB_USR_001",
        role="scientific_user",
        environment_id="env_01",
        adapter_name="direct_qa",
        dimension_scores=DimensionScores(
            outcome=0.9,
            tool_use=0.8,
            grounding=0.7,
            governance=1.0,
            efficiency=0.85,
            robustness=None,
        ),
        aggregate_score=0.87,
        timestamp=datetime(2026, 3, 19, 10, 0, 5, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLangfuseExporterInit:
    def test_missing_langfuse_package_raises_import_error(self, monkeypatch):
        """ImportError raised when langfuse is not installed."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "langfuse":
                raise ImportError("No module named 'langfuse'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        from exabench.exporters import langfuse_exporter
        import importlib
        importlib.reload(langfuse_exporter)

        with pytest.raises(ImportError, match="langfuse is not installed"):
            langfuse_exporter.LangfuseExporter(
                public_key="pk-lf-test",
                secret_key="sk-lf-test",
            )

    def test_missing_credentials_raises_value_error(self, monkeypatch):
        """ValueError raised when credentials are absent."""
        monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

        mock_lf_module = MagicMock()
        with patch.dict("sys.modules", {"langfuse": mock_lf_module}):
            from exabench.exporters import langfuse_exporter
            import importlib
            importlib.reload(langfuse_exporter)

            with pytest.raises(ValueError, match="Langfuse credentials missing"):
                langfuse_exporter.LangfuseExporter()

    def test_credentials_from_env(self, monkeypatch):
        """Exporter reads credentials from environment variables."""
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-from-env")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-from-env")

        mock_lf_class = MagicMock()
        mock_lf_module = MagicMock()
        mock_lf_module.Langfuse = mock_lf_class

        with patch.dict("sys.modules", {"langfuse": mock_lf_module}):
            from exabench.exporters import langfuse_exporter
            import importlib
            importlib.reload(langfuse_exporter)

            langfuse_exporter.LangfuseExporter()

        mock_lf_class.assert_called_once_with(
            public_key="pk-from-env",
            secret_key="sk-from-env",
        )

    def test_host_kwarg_passed_when_set(self, monkeypatch):
        """LANGFUSE_HOST is forwarded to the Langfuse client."""
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-x")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-x")
        monkeypatch.setenv("LANGFUSE_HOST", "http://localhost:3000")

        mock_lf_class = MagicMock()
        mock_lf_module = MagicMock()
        mock_lf_module.Langfuse = mock_lf_class

        with patch.dict("sys.modules", {"langfuse": mock_lf_module}):
            from exabench.exporters import langfuse_exporter
            import importlib
            importlib.reload(langfuse_exporter)

            langfuse_exporter.LangfuseExporter()

        mock_lf_class.assert_called_once_with(
            public_key="pk-x",
            secret_key="sk-x",
            host="http://localhost:3000",
        )


class TestLangfuseExporterExport:
    def _make_exporter(self):
        mock_lf_class = MagicMock()
        mock_lf_module = MagicMock()
        mock_lf_module.Langfuse = mock_lf_class

        with patch.dict("sys.modules", {"langfuse": mock_lf_module}):
            from exabench.exporters import langfuse_exporter
            import importlib
            importlib.reload(langfuse_exporter)
            exporter = langfuse_exporter.LangfuseExporter(
                public_key="pk-test",
                secret_key="sk-test",
            )
        return exporter, mock_lf_class.return_value  # exporter, mock lf instance

    def test_export_creates_trace(self):
        exporter, mock_lf = self._make_exporter()
        task = _make_task()
        trace = _make_trace()
        result = _make_result()

        exporter.export(trace, result, task)

        mock_lf.trace.assert_called_once()
        call_kwargs = mock_lf.trace.call_args.kwargs
        assert call_kwargs["id"] == "trace-abc"
        assert call_kwargs["name"] == "JOB_USR_001"
        assert call_kwargs["session_id"] == "run-xyz"
        assert call_kwargs["user_id"] == "scientific_user"

    def test_export_creates_spans_for_each_step(self):
        exporter, mock_lf = self._make_exporter()
        mock_trace_obj = mock_lf.trace.return_value

        exporter.export(_make_trace(), _make_result(), _make_task())

        # Two steps → two span() calls
        assert mock_trace_obj.span.call_count == 2

    def test_export_creates_generation_when_tokens_present(self):
        exporter, mock_lf = self._make_exporter()
        mock_trace_obj = mock_lf.trace.return_value

        exporter.export(_make_trace(), _make_result(), _make_task())

        mock_trace_obj.generation.assert_called_once()
        gen_kwargs = mock_trace_obj.generation.call_args.kwargs
        assert gen_kwargs["model"] == "gpt-4o"
        assert gen_kwargs["usage"]["input"] == 150
        assert gen_kwargs["usage"]["output"] == 50

    def test_export_attaches_dimension_scores(self):
        exporter, mock_lf = self._make_exporter()
        mock_trace_obj = mock_lf.trace.return_value

        exporter.export(_make_trace(), _make_result(), _make_task())

        score_calls = {c.kwargs["name"]: c.kwargs["value"] for c in mock_trace_obj.score.call_args_list}
        assert score_calls["outcome"] == pytest.approx(0.9)
        assert score_calls["tool_use"] == pytest.approx(0.8)
        assert score_calls["governance"] == pytest.approx(1.0)
        assert score_calls["aggregate"] == pytest.approx(0.87)
        # robustness is None → should not appear
        assert "robustness" not in score_calls

    def test_export_skips_generation_when_no_tokens(self):
        exporter, mock_lf = self._make_exporter()
        mock_trace_obj = mock_lf.trace.return_value

        trace = _make_trace()
        trace.total_tokens = None

        exporter.export(trace, _make_result(), _make_task())

        mock_trace_obj.generation.assert_not_called()

    def test_flush_delegates_to_langfuse(self):
        exporter, mock_lf = self._make_exporter()
        exporter.flush()
        mock_lf.flush.assert_called_once()
