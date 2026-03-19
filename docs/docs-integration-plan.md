# Documentation Integration Plan

**Status:** Completed (full integration executed)

**Problem:** Too many overlapping markdown files in `docs/framework/` and `docs/taxonomy/` lead to hard-to-follow docs and inconsistent definitions.

**Goal:** Fewer files, single source of truth, clear structure, consistent architecture.

---

## 1. Current Issues

### Duplication
| Location | Issue |
|---------|-------|
| **03_architecture.md** | ~2744 lines — whole sections duplicated (e.g. "Benchmark Design Principles" appears twice). Contains merged content from 07 (Software Architecture). |
| **permissions_access_control.md** (framework) | Nearly identical to **taxonomy/04_access_control.md** — same RBAC tables and content. |
| ~~hpc_multi_variant_query_usecases.md~~ | Removed — was duplicate of `taxonomy/benchmark_query_metadata_schema.md`. |

### Missing or broken
- Index references 04, 05, 07 — 04 is in taxonomy, 05 doesn't exist, 07 content is merged into 03.
- Index uses Obsidian-style links that don't resolve to actual files.

### Scattered definitions
- Principles, roles, v0.1 scope appear in 00, 03, README — not always identical.
- "ExaBench is..." stated differently across files.

---

## 2. Proposed Integrated Structure

Reduce to **6–7 core documents** with clear ownership:

```
docs/
├── README.md                    # Entry point: what to read, where to find things
│
├── framework/
│   ├── 01-overview.md           # What ExaBench is, principles, positioning (merge 00 + index + intro from 01)
│   ├── 02-background.md         # Motivation, related work (01 + 02, condensed)
│   ├── 03-architecture.md       # Benchmark design: layers, entities, workflow (deduplicated 03)
│   ├── 04-implementation.md     # Software architecture, CLI, adapters, tools (extracted 07 from 03)
│   ├── 05-environments.md       # Environment snapshots (06, unchanged)
│   ├── 06-evaluation.md        # Evaluation protocol, metrics, trace schema (08, unchanged)
│   └── 07-taxonomy.md           # Roles, categories, access control, query schema (consolidate taxonomy/)
│
├── roadmap.md                   # Unchanged
├── architecture-clarification.md # Unchanged (or merge into 01/04)
├── chat-outcomes.md             # Unchanged
└── docs-integration-plan.md     # This file
```

### Rationale

| New file | Merges | Single source for |
|----------|--------|-------------------|
| **01-overview** | 00, index, positioning from 01 | What ExaBench is, principles, v0.1 scope |
| **02-background** | 01 (condensed), 02 | Motivation, related work |
| **03-architecture** | 03 (deduplicated only) | Benchmark layers, entities, execution workflow |
| **04-implementation** | 07 (from 03) | Software architecture, adapters, runner, tools |
| **05-environments** | 06 | Snapshot format, loading |
| **06-evaluation** | 08 | Scoring, trace, pass/fail |
| **07-taxonomy** | taxonomy/*, permissions | Roles, QCATs, RBAC, query schema |

---

## 3. Deduplication Priorities

### High impact
1. **03_architecture.md** — Remove duplicated sections (keep one copy of each). Split out 07 content into 04-implementation.md.
2. **Access control** — Keep one file. Recommended: `framework/07-taxonomy.md` with an "Access Control" section. Delete `permissions_access_control.md` and `taxonomy/04_access_control.md`.
3. **Query schema** — `benchmark_query_metadata_schema.md` is canonical; merge into taxonomy section of 07-taxonomy.md.

### Definition freeze
Create **one** canonical definition block in 01-overview.md:
- ExaBench positioning (one sentence)
- Five benchmark principles
- v0.1 scope (roles, categories, baselines)
- Other docs reference this; they do not redefine.

---

## 4. Implementation Order

| Step | Action | Effort |
|------|--------|--------|
| 1 | Create 01-overview.md from 00 + index | Low |
| 2 | Deduplicate 03_architecture.md (remove duplicate sections) | Medium |
| 3 | Extract 07 content from 03 → new 04-implementation.md | Medium |
| 4 | Consolidate taxonomy: merge roles, access control, query schema → 07-taxonomy.md | Medium |
| 5 | Merge permissions_access_control + 04_access_control → one section | Low |
| 6 | Merge benchmark_query_metadata_schema into 07-taxonomy | Low |
| 7 | Rename 06, 08 for consistency (05-environments, 06-evaluation) | Low |
| 8 | Update index/README with correct links | Low |
| 9 | Archive or remove superseded files | Low |

---

## 5. Optional: Minimal Change

If full integration is too much for now, a **minimal** fix:

1. **Deduplicate 03** — Remove the repeated sections (saves ~800 lines).
2. **Merge access control** — Keep one file, delete the other.
3. **Fix index.md** — Use correct relative links (`./00_project_framing.md` etc.).
4. **Add docs/README.md** — Simple table: "Read this for X" → links to the right files.

---

## 6. Files to Archive (after integration)

- `framework/permissions_access_control.md` (→ merged into taxonomy)
- `taxonomy/04_access_control.md` (→ merged)
- ~~framework/hpc_multi_variant_query_usecases.md~~ (removed — was duplicate)
- `taxonomy/benchmark_query_metadata_schema.md` (→ merged)
- Original 00, 01, 02, 03, 06, 08 (after content moved to new structure)

Move to `docs/archive/` rather than delete, for reference.
