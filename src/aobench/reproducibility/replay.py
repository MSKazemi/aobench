"""Deterministic replay engine — cassette record/replay (Feature 24, ADR 0005).

Records every non-deterministic response (LLM completion, tool result) keyed by
``(task_id, env_id, seed, model_snapshot, prompt)`` so a run can be replayed
bit-for-bit with zero API cost — for cheap CI, offline regrading, and
reproducible scores.

This module is the reusable primitive (pure: ``json``/``hashlib`` only).
Adapters call ``ReplaySession.respond(key, producer)``:

    key = make_key(task_id=..., env_id=..., seed=..., model=..., prompt=...)
    completion = session.respond(key, lambda: real_llm_call(prompt))

- **live**  → call the producer, record the result, return it.
- **replay** → serve the recorded result; raise ``ReplayMiss`` if absent.
- **auto**  → serve if recorded, else call+record (top-up mode).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Optional

Mode = str  # "live" | "replay" | "auto"


class ReplayMiss(KeyError):
    """Raised in replay mode when a key has no recorded response."""


def make_key(
    *,
    task_id: str,
    env_id: str,
    model: str,
    prompt: Any,
    seed: Optional[int] = None,
    extra: Optional[dict[str, Any]] = None,
) -> str:
    """Return a stable sha256 hex key for a cassette entry.

    ``prompt`` may be a string or any JSON-serialisable structure (messages).
    """
    payload = {
        "task_id": task_id,
        "env_id": env_id,
        "model": model,
        "seed": seed,
        "prompt": prompt,
        "extra": extra or {},
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class Cassette:
    """A JSON-backed key→response store."""

    def __init__(self, entries: Optional[dict[str, Any]] = None,
                 path: Optional[str | Path] = None) -> None:
        self._entries: dict[str, Any] = dict(entries or {})
        self._path: Optional[Path] = Path(path) if path else None

    # -- dict-ish access --
    def __contains__(self, key: str) -> bool:
        return key in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    def get(self, key: str) -> Any:
        return self._entries.get(key)

    def put(self, key: str, value: Any) -> None:
        self._entries[key] = value

    # -- persistence --
    @classmethod
    def load(cls, path: str | Path) -> "Cassette":
        p = Path(path)
        entries = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        return cls(entries=entries, path=p)

    def save(self, path: Optional[str | Path] = None) -> Path:
        target = Path(path) if path else self._path
        if target is None:
            raise ValueError("no path provided to save cassette")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self._entries, sort_keys=True, indent=2, default=str), encoding="utf-8")
        self._path = target
        return target


class ReplaySession:
    """Wraps a cassette with a replay mode and a ``respond`` gate."""

    def __init__(self, cassette: Optional[Cassette] = None, mode: Mode = "live") -> None:
        if mode not in ("live", "replay", "auto"):
            raise ValueError(f"invalid mode {mode!r}; use live|replay|auto")
        self.cassette = cassette if cassette is not None else Cassette()
        self.mode = mode
        self.hits = 0
        self.misses = 0
        self.recorded = 0

    def respond(self, key: str, producer: Callable[[], Any]) -> Any:
        """Return a response for ``key`` per the session mode."""
        if self.mode == "replay":
            if key in self.cassette:
                self.hits += 1
                return self.cassette.get(key)
            self.misses += 1
            raise ReplayMiss(key)

        if self.mode == "auto" and key in self.cassette:
            self.hits += 1
            return self.cassette.get(key)

        # live, or auto-miss: produce and record.
        value = producer()
        self.cassette.put(key, value)
        self.recorded += 1
        return value

    def stats(self) -> dict[str, int]:
        return {"hits": self.hits, "misses": self.misses, "recorded": self.recorded,
                "size": len(self.cassette)}
