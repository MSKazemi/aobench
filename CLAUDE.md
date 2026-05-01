- If you add a new command (e.g., a script or CLI entry point), also add a corresponding target to the Makefile.
- If you add or update a command, also add or update it in `docs/COMMANDS.md`.
- When you implement, change, or remove significant functionality (e.g., scorers, adapters, tools, schemas), update the relevant docs: `docs/roadmap.md`, `docs/framework/` (architecture, evaluation), and any architecture diagrams.
- When adding a model baseline, wire it through the existing `_build_adapter()` registry in `src/exabench/cli/run_cmd.py` — do not create a new adapter file unless the protocol differs. vLLM open-weight models use `OpenAIAdapter` with `OPENAI_BASE_URL` override.
- Pin a git tag (`v0.1.0`, `v0.1.1`, …) before any paper-cited experiment run. Record tag + commit hash in `data/runs/<run-id>/manifest.json`.
- The dataset split file `benchmark/tasks/dataset_splits.py` is **frozen**. Do not modify the split lists. The 30% test split is run exactly once — after all dev-split paper claims are locked — and reported verbatim without retuning.
- Paper-writing rules live in the sibling repo `ExaBench-SoA/CLAUDE.md`, not here.
---

## Local Claude Context

Project-specific memory lives in `.claude/` (gitignored):

```
.claude/
└── memory/    # Auto-memory — read/written by Claude Code across sessions
```

The `~/.claude/projects/.../memory` harness path is a symlink → `.claude/memory/`.
