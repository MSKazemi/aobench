"""AOBench Gymnasium-compatible environment (gymnasium_env_spec §11).

AOBenchEnv wraps one (task, environment) pair as a standard Gym loop:

    env = AOBenchEnv()
    obs, info = env.reset(env_id="env_01", task_id="JOB_USR_001", seed=42)
    while True:
        action = agent.act(obs)
        obs, reward, terminated, truncated, info = env.step(action)
        if terminated or truncated:
            break

Action dict keys:
    type          : "tool_call" | "message" | "finish"
    tool_name     : str  (tool_call only)
    method        : str  (tool_call only)
    arguments     : str  (JSON-encoded dict, tool_call only)
    message       : str  (message type)
    finish_answer : str  (finish type)

Observation dict keys:
    task_query       : str
    role             : str
    environment_id   : str
    last_tool_result : str   (JSON/text of last tool observation)
    step_count       : int

info keys:
    engaged          : bool  — True once the agent calls a tool from task.expected_tool_calls
    hard_fail        : bool
    violations       : list[str]
    task_id          : str
    env_id           : str
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Optional

from aobench.gym.spaces import ACTION_SPACE, OBSERVATION_SPACE, DictSpace
from aobench.loaders.env_loader import load_environment
from aobench.loaders.task_loader import load_task
from aobench.environment.snapshot_loader import build_tool_registry
from aobench.schemas.task import TaskSpec
from aobench.schemas.trace import Trace, TraceStep, ToolCall
from aobench.scorers.engagement import is_engaged


class AOBenchEnv:
    """Gymnasium-compatible AOBench environment.

    Compatible with the gymnasium.Env interface without requiring the
    gymnasium package (though it can be used with it transparently).
    """

    metadata: dict[str, Any] = {"render_modes": []}

    # These match gymnasium.Env expectations
    observation_space: DictSpace = OBSERVATION_SPACE
    action_space: DictSpace = ACTION_SPACE

    _MAX_STEPS = 20  # truncation limit per episode

    def __init__(
        self,
        task_dir: str | Path = "benchmark/tasks/specs",
        env_dir: str | Path = "benchmark/environments",
    ) -> None:
        self._task_dir = Path(task_dir)
        self._env_dir = Path(env_dir)

        # State set by reset()
        self._task: Optional[TaskSpec] = None
        self._registry = None
        self._step_count: int = 0
        self._terminated: bool = False
        self._trace_steps: list[TraceStep] = []
        self._last_result: str = ""
        self._hard_fail: bool = False
        self._violations: list[str] = []
        self._engaged: bool = False
        self._rng: random.Random = random.Random()

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def reset(
        self,
        env_id: str | None = None,
        task_id: str | None = None,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Reset the environment for a new episode.

        Args:
            env_id:  Environment snapshot ID (e.g. "env_01").
            task_id: Task ID to evaluate (e.g. "JOB_USR_001").
            seed:    RNG seed for determinism.
            options: Optional extra config dict (currently unused).

        Returns:
            (observation, info)
        """
        if seed is not None:
            self._rng = random.Random(seed)

        if task_id is None:
            raise ValueError("task_id is required")

        task_path = self._task_dir / f"{task_id}.json"
        self._task = load_task(str(task_path))

        resolved_env_id = env_id or self._task.environment_id
        env_bundle = load_environment(str(self._env_dir / resolved_env_id))
        role = self._task.role
        self._registry = build_tool_registry(
            env_bundle, role=role, allowed_tools=self._task.allowed_tools
        )

        self._step_count = 0
        self._terminated = False
        self._trace_steps = []
        self._last_result = ""
        self._hard_fail = False
        self._violations = []
        self._engaged = False

        obs = self._make_obs()
        info = self._make_info()
        return obs, info

    def step(
        self, action: dict[str, Any]
    ) -> tuple[dict[str, Any], float, bool, bool, dict[str, Any]]:
        """Execute one action in the environment.

        Args:
            action: Dict with keys: type, tool_name, method, arguments,
                    message, finish_answer.

        Returns:
            (observation, reward, terminated, truncated, info)
        """
        if self._task is None:
            raise RuntimeError("Call reset() before step()")
        if self._terminated:
            raise RuntimeError("Episode already terminated — call reset()")

        action_type = action.get("type", "message")
        self._step_count += 1

        if action_type == "tool_call":
            obs, reward = self._handle_tool_call(action)
        elif action_type == "finish":
            obs, reward = self._handle_finish(action)
        else:
            # message: no tool call, no finish
            self._last_result = ""
            obs = self._make_obs()
            reward = 0.0

        truncated = self._step_count >= self._MAX_STEPS and not self._terminated
        terminated = self._terminated

        return obs, reward, terminated, truncated, self._make_info()

    def render(self) -> None:
        """No-op render."""

    def close(self) -> None:
        """Release resources."""
        self._registry = None
        self._task = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _handle_tool_call(
        self, action: dict[str, Any]
    ) -> tuple[dict[str, Any], float]:
        assert self._task is not None
        tool_name = action.get("tool_name", "")
        method = action.get("method", "")
        try:
            args = json.loads(action.get("arguments", "{}"))
        except (json.JSONDecodeError, TypeError):
            args = {}

        # Emit trace step
        tc = ToolCall(tool_name=tool_name, method=method, arguments=args)
        step = TraceStep(
            step_id=self._step_count,
            span_id=f"step_{self._step_count:03d}",
            step_type="tool_call",
            tool_call=tc,
        )
        self._trace_steps.append(step)

        # Check engagement: once engaged, stays engaged
        if not self._engaged and self._task.expected_tool_calls:
            if tool_name in self._task.expected_tool_calls:
                self._engaged = True

        # Invoke the tool
        if self._registry is not None and tool_name in (
            getattr(self._registry, "allowed_tools", None) or []
        ):
            try:
                result = self._registry.invoke(tool_name, method, args)
                obs_content = str(result)
                if getattr(result, "permission_denied", False):
                    self._violations.append(f"permission_denied:{tool_name}.{method}")
            except Exception as e:
                obs_content = f"tool_error: {e}"
        else:
            obs_content = f"tool_not_allowed: {tool_name}"
            self._violations.append(f"forbidden_tool:{tool_name}")

        self._last_result = obs_content[:2000]  # truncate large responses
        obs = self._make_obs()
        return obs, 0.0

    def _handle_finish(
        self, action: dict[str, Any]
    ) -> tuple[dict[str, Any], float]:
        self._terminated = True
        answer = action.get("finish_answer", "")
        self._last_result = f"FINISHED: {answer}"
        obs = self._make_obs()
        reward = 1.0 if not self._violations else 0.0
        return obs, reward

    def _make_obs(self) -> dict[str, Any]:
        assert self._task is not None
        return {
            "task_query":       self._task.query_text,
            "role":             self._task.role,
            "environment_id":   self._task.environment_id,
            "last_tool_result": self._last_result,
            "step_count":       self._step_count,
        }

    def _make_info(self) -> dict[str, Any]:
        assert self._task is not None
        return {
            "engaged":    self._engaged,
            "hard_fail":  self._hard_fail,
            "violations": list(self._violations),
            "task_id":    self._task.task_id,
            "env_id":     self._task.environment_id,
            "step_count": self._step_count,
        }
