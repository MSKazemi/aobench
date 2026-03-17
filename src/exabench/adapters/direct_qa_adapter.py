"""Direct QA baseline adapter — answers without any tool calls (no LLM required)."""

from __future__ import annotations

from datetime import datetime, timezone

from exabench.adapters.base import BaseAdapter
from exabench.schemas.trace import Trace, TraceStep
from exabench.utils.ids import make_trace_id


class DirectQAAdapter(BaseAdapter):
    """Baseline: returns a placeholder answer with zero tool calls.

    Useful for establishing a no-tools lower bound and for testing the pipeline
    without needing any LLM API keys.
    """

    name = "direct_qa"

    def __init__(self, answer: str = "[DirectQA: no answer provided]") -> None:
        self._answer = answer

    def run(self, context: "ExecutionContext") -> Trace:  # type: ignore[name-defined]
        now = datetime.now(tz=timezone.utc)
        return Trace(
            trace_id=make_trace_id(),
            run_id=context.run_id,
            task_id=context.task.task_id,
            role=context.task.role,
            environment_id=context.env.metadata.environment_id,
            adapter_name=self.name,
            steps=[
                TraceStep(
                    step_id=1,
                    reasoning="Direct QA baseline: answering without tool use.",
                    tool_call=None,
                    observation=None,
                    timestamp=now,
                )
            ],
            final_answer=self._answer,
            start_time=now,
            end_time=now,
            total_tokens=0,
            hard_fail=False,
        )
