# 04-Implementation Improvements

**Current state:** ~1839 lines, merged from multiple sources. Good content but needs structure, deduplication, and alignment with current codebase.

**Quick wins (completed):** TOC added, CLI examples updated, cross-refs fixed (08→06), repository structure replaced, Adapter clarification added.

---

## 1. Structural issues

### 1.1 Chaotic heading hierarchy

- Mixed numbering: `# 1`, `# 2`, `# 3` then `# 2. Initial Architecture` reappears
- `## 1 — Scope` nested under `# 2`
- CLI subsections numbered `13.1`–`13.5` but there is no section 13
- "Core Components" (A–H) repeated in different places

**Fix:** Define a single clear outline, e.g.:

```
# 04 — Implementation
## 1. Purpose & Scope
## 2. CLI Design
## 3. Runtime Layers & Architecture
## 4. Execution Workflow
## 5. Component Responsibilities
## 6. Interfaces & Contracts
## 7. Design Principles & v0.1 Boundaries
## 8. FAQs (API, MCP, A2A, databases)
## 9. Definition of Done
```

---

## 2. Duplicate content

| Content | Appears | Action |
|--------|---------|--------|
| Component list (Task, Env, Tool, Adapter, Runner, Trace, Scorer, Report) | §3 "Important parts" + §6 "Core Components" | Keep one; reference the other |
| Repository structure | §6.8 (old layout) | Replace with actual structure from README/03 |
| "Do you need API/databases/MCP/A2A" | Scattered, repeated | Consolidate into one FAQ section |
| High-level architecture diagram | Two similar ASCII diagrams | Keep one; optionally add a link to a Mermaid version |

---

## 3. Outdated references

### 3.1 CLI examples

| Current | Actual |
|---------|--------|
| `--tasks data/tasks/tasks.json` | `exabench validate benchmark` (no `--tasks`) |
| `--environments data/environments/` | Uses `benchmark/` path |
| `--agent exabench.agents.openai_adapter:OpenAIAdapter` | `exabench.adapters.openai_adapter.OpenAIAdapter` |
| `--qcats`, `--splits` | Check if implemented in CLI |

**Fix:** Match examples to current `exabench run task`, `exabench validate benchmark`, etc.

### 3.2 Repository structure (section 6.8)

Current doc shows:
```
exabench/
  tasks/
  environments/
  ...
```

Actual layout (from README):
```
src/exabench/
  schemas/, loaders/, tools/, adapters/, runners/, scorers/, cli/
benchmark/
  tasks/specs/, environments/, configs/, qa/
```

**Fix:** Replace with actual layout and point to [03-architecture](03-architecture.md) §11.

### 3.3 Cross-references

- `08 — Evaluation Protocol` → [06 — Evaluation](06-evaluation.md)
- `07 — Tool Architecture` → this page (04)

---

## 4. Adapter section alignment

Per [architecture-clarification](architecture-clarification.md):

- **Primary:** Connect to external agents (ODA, ExaSage) via HTTP/MCP
- **Baselines:** OpenAIAdapter, direct_qa for development and pipeline validation

**Fix:** In §D Agent Adapter Layer, add:

> **Primary use case:** ExaBench connects to deployed HPC agents (ODA, ExaSage, etc.) via HTTP, MCP, or other protocols. **Baseline adapters** (OpenAIAdapter, direct_qa) exist for developing and validating the benchmark when no external agent is available.

---

## 5. Tone consistency

Current mix:
- "You need a standard interface..." (second person)
- "The benchmark runner must..." (formal)
- "This is the heart of the software system." (informal)

**Fix:** Prefer one style (e.g. direct/imperative: "The adapter must..." or consistent "you").

---

## 6. Recommended action plan

| Priority | Action | Effort |
|----------|--------|--------|
| **High** | Fix CLI examples to match current commands | Low |
| **High** | Replace repository structure with actual layout | Low |
| **High** | Fix cross-references (08→06) | Low |
| **Medium** | Add table of contents at top | Low |
| **Medium** | Consolidate duplicate component lists | Medium |
| **Medium** | Align Adapter section with architecture-clarification | Low |
| **Lower** | Reorganize into single clear outline | Medium |
| **Lower** | Consolidate FAQ sections (API, MCP, A2A, DB) | Medium |

---

## 7. Quick wins (minimal edit)

1. Add TOC after Purpose.
2. Fix `08` → `06` and `07` → `04` everywhere.
3. Update CLI examples to real commands.
4. Replace §6.8 repository block with link to 03-architecture §11.
5. Add one paragraph in Adapter section about primary vs baseline adapters.
