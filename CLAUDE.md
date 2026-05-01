- If you add a new command (e.g., a script or CLI entry point), also add a corresponding target to the Makefile.
- If you add or update a command, also add or update it in `docs/COMMANDS.md`.
- When you implement, change, or remove significant functionality (e.g., scorers, adapters, tools, schemas), update the relevant docs: `docs/roadmap.md`, `docs/framework/` (architecture, evaluation), and any architecture diagrams.
---

## Local Claude Context

Project-specific memory lives in `.claude/` (gitignored):

```
.claude/
└── memory/    # Auto-memory — read/written by Claude Code across sessions
```

The `~/.claude/projects/.../memory` harness path is a symlink → `.claude/memory/`.
