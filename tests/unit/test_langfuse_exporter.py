"""Unit tests for LangfuseExporter (Langfuse SDK v4)."""

from __future__ import annotations

from contextlib import contextmanager
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
# Helper: build a mock Langfuse v4 client + exporter
# ---------------------------------------------------------------------------

def _build_mock_exporter():
    """Return (exporter, mock_lf_instance, mock_root_span)."""
    import importlib
    import sys

    # Build a mock root span that acts as a context manager
    mock_root_span = MagicMock()
    mock_root_span.__enter__ = lambda s: mock_root_span
    mock_root_span.__exit__ = MagicMock(return_value=False)

    # Child observations also act as context managers
    mock_child_span = MagicMock()
    mock_child_span.__enter__ = lambda s: mock_child_span
    mock_child_span.__exit__ = MagicMock(return_value=False)
    mock_root_span.start_as_current_observation.return_value = mock_child_span

    # Langfuse client
    mock_lf_instance = MagicMock()
    mock_lf_instance.start_as_current_observation.return_value = mock_root_span

    mock_lf_class = MagicMock(return_value=mock_lf_instance)

    # Mock OTel span attributes
    mock_attrs = MagicMock()
    mock_attrs.TRACE_SESSION_ID = "langfuse.trace.session_id"
    mock_attrs.TRACE_USER_ID = "langfuse.trace.user_id"
    mock_attrs.TRACE_TAGS = "langfuse.trace.tags"

    mock_lf_module = MagicMock()
    mock_lf_module.Langfuse = mock_lf_class
    mock_lf_module.LangfuseOtelSpanAttributes = mock_attrs

    with patch.dict(sys.modules, {
        "langfuse": mock_lf_module,
    }):
        from exabench.exporters import langfuse_exporter
        importlib.reload(langfuse_exporter)
        exporter = langfuse_exporter.LangfuseExporter(
            public_key="pk-test",
            secret_key="sk-test",
        )

    return exporter, mock_lf_instance, mock_root_span


# ---------------------------------------------------------------------------
# Init tests
# ---------------------------------------------------------------------------

class TestLangfuseExporterInit:
    def test_missing_langfuse_package_raises_import_error(self, monkeypatch):
        import builtins, importlib
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "langfuse":
                raise ImportError("No module named 'langfuse'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        from exabench.exporters import langfuse_exporter
        importlib.reload(langfuse_exporter)

        with pytest.raises(ImportError, match="langfuse is not installed"):
            langfuse_exporter.LangfuseExporter(public_key="pk-lf-test", secret_key="sk-lf-test")

    def test_missing_credentials_raises_value_error(self, monkeypatch):
        import importlib, sys
        monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

        mock_lf_module = MagicMock()
        with patch.dict(sys.modules, {"langfuse": mock_lf_module}):
            from exabench.exporters import langfuse_exporter
            importlib.reload(langfuse_exporter)
            with pytest.raises(ValueError, match="Langfuse credentials missing"):
                langfuse_exporter.LangfuseExporter()

    def test_credentials_from_env(self, monkeypatch):
        import importlib, sys
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-from-env")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-from-env")
        monkeypatch.delenv("LANGFUSE_HOST", raising=False)
        monkeypatch.delenv("LANGFUSE_BASE_URL", raising=False)

        mock_lf_class = MagicMock()
        mock_lf_module = MagicMock()
        mock_lf_module.Langfuse = mock_lf_class

        with patch.dict(sys.modules, {"langfuse": mock_lf_module}):
            from exabench.exporters import langfuse_exporter
            importlib.reload(langfuse_exporter)
            langfuse_exporter.LangfuseExporter()

        mock_lf_class.assert_called_once_with(public_key="pk-from-env", secret_key="sk-from-env")

    def test_langfuse_base_url_env_accepted(self, monkeypatch):
        """LANGFUSE_BASE_URL (shown by Langfuse UI) is accepted alongside LANGFUSE_HOST."""
        import importlib, sys
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-x")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-x")
        monkeypatch.delenv("LANGFUSE_HOST", raising=False)
        monkeypatch.setenv("LANGFUSE_BASE_URL", "http://localhost:3000")

        mock_lf_class = MagicMock()
        mock_lf_module = MagicMock()
        mock_lf_module.Langfuse = mock_lf_class

        with patch.dict(sys.modules, {"langfuse": mock_lf_module}):
            from exabench.exporters import langfuse_exporter
            importlib.reload(langfuse_exporter)
            langfuse_exporter.LangfuseExporter()

        mock_lf_class.assert_called_once_with(
            public_key="pk-x", secret_key="sk-x", host="http://localhost:3000"
        )

    def test_langfuse_host_takes_priority_over_base_url(self, monkeypatch):
        """LANGFUSE_HOST takes precedence over LANGFUSE_BASE_URL."""
        import importlib, sys
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-x")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-x")
        monkeypatch.setenv("LANGFUSE_HOST", "http://host-value:3000")
        monkeypatch.setenv("LANGFUSE_BASE_URL", "http://base-url-value:3000")

        mock_lf_class = MagicMock()
        mock_lf_module = MagicMock()
        mock_lf_module.Langfuse = mock_lf_class

        with patch.dict(sys.modules, {"langfuse": mock_lf_module}):
            from exabench.exporters import langfuse_exporter
            importlib.reload(langfuse_exporter)
            langfuse_exporter.LangfuseExporter()

        call_kwargs = mock_lf_class.call_args.kwargs
        assert call_kwargs["host"] == "http://host-value:3000"


# ---------------------------------------------------------------------------
# Export tests
# ---------------------------------------------------------------------------

class TestLangfuseExporterExport:
    def test_export_creates_root_observation(self):
        exporter, mock_lf, _ = _build_mock_exporter()
        exporter.export(_make_trace(), _make_result(), _make_task())

        mock_lf.start_as_current_observation.assert_called_once()
        call_kwargs = mock_lf.start_as_current_observation.call_args.kwargs
        assert call_kwargs["name"] == "JOB_USR_001"
        # ExaBench trace_id is stored in metadata (not passed as trace_context)
        assert "trace_context" not in call_kwargs
        assert call_kwargs["metadata"]["exabench_trace_id"] == "trace-abc"

    def test_export_creates_child_spans_per_step(self):
        exporter, _, mock_root = _build_mock_exporter()
        exporter.export(_make_trace(), _make_result(), _make_task())

        # 2 steps + 1 generation = 3 child observations
        assert mock_root.start_as_current_observation.call_count == 3

    def test_tool_step_uses_tool_as_type(self):
        exporter, _, mock_root = _build_mock_exporter()
        exporter.export(_make_trace(), _make_result(), _make_task())

        calls = mock_root.start_as_current_observation.call_args_list
        # First call = step-0 (has tool_call) → as_type="tool"
        assert calls[0].kwargs["as_type"] == "tool"
        assert "slurm" in calls[0].kwargs["name"]

    def test_non_tool_step_uses_span_as_type(self):
        exporter, _, mock_root = _build_mock_exporter()
        exporter.export(_make_trace(), _make_result(), _make_task())

        calls = mock_root.start_as_current_observation.call_args_list
        # Second call = step-1 (no tool_call) → as_type="span"
        assert calls[1].kwargs["as_type"] == "span"

    def test_generation_created_when_tokens_present(self):
        exporter, _, mock_root = _build_mock_exporter()
        exporter.export(_make_trace(), _make_result(), _make_task())

        calls = mock_root.start_as_current_observation.call_args_list
        # Last call = generation
        gen_call = calls[-1].kwargs
        assert gen_call["as_type"] == "generation"
        assert gen_call["model"] == "gpt-4o"
        assert gen_call["usage_details"]["input"] == 150
        assert gen_call["usage_details"]["output"] == 50

    def test_generation_skipped_when_no_tokens(self):
        exporter, _, mock_root = _build_mock_exporter()
        trace = _make_trace()
        trace.total_tokens = None
        exporter.export(trace, _make_result(), _make_task())

        # Only 2 step spans, no generation
        assert mock_root.start_as_current_observation.call_count == 2

    def test_dimension_scores_attached_to_trace(self):
        exporter, _, mock_root = _build_mock_exporter()
        exporter.export(_make_trace(), _make_result(), _make_task())

        score_calls = {c.kwargs["name"]: c.kwargs["value"]
                       for c in mock_root.score_trace.call_args_list}
        assert score_calls["outcome"] == pytest.approx(0.9)
        assert score_calls["tool_use"] == pytest.approx(0.8)
        assert score_calls["governance"] == pytest.approx(1.0)
        assert score_calls["aggregate"] == pytest.approx(0.87)
        # robustness is None → must not appear
        assert "robustness" not in score_calls

    def test_flush_delegates_to_client(self):
        exporter, mock_lf, _ = _build_mock_exporter()
        exporter.flush()
        mock_lf.flush.assert_called_once()
