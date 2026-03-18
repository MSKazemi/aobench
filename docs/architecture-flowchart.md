# ExaBench Architecture Flowchart

This document contains architecture diagrams reflecting the **implemented** ExaBench system (Alpha-0 / v0.1).

---

## 1. System Overview

```mermaid
graph TB
    subgraph CLI["CLI Layer (exabench)"]
        RUN["exabench run task/all"]
        VAL["exabench validate benchmark"]
        REP["exabench report json/html/slices"]
        CMP["exabench compare runs"]
        ROB["exabench robustness task"]
    end

    subgraph BENCH["Benchmark Dataset (benchmark/)"]
        TASKS["tasks/specs/*.json\n(12 TaskSpecs)"]
        ENVS["environments/env_01…05/\n(5 Snapshots)"]
        CFGS["configs/\nscoring_profiles.yaml\ntool_registry.yaml"]
    end

    subgraph CORE["Core Pipeline (src/exabench/)"]
        LOADER["Loaders\nTaskLoader · EnvLoader\nBenchmarkRegistry"]
        RUNNER["BenchmarkRunner"]
        ADAPTER["Adapter\ndirect_qa | openai"]
        TOOLS["ToolRegistry\n+ Mock Tools"]
        SCORERS["Scoring Engine\nAggregateScorer"]
        WRITER["TraceWriter"]
    end

    subgraph ARTIFACTS["Runtime Artifacts (data/runs/<run_id>/)"]
        TRACE["traces/<task_id>_trace.json"]
        RESULT["results/<task_id>_result.json"]
        SUMMARY["run_summary.json"]
        HTML["report.html"]
    end

    RUN --> RUNNER
    VAL --> LOADER
    REP --> SUMMARY
    REP --> HTML
    CMP --> RESULT
    ROB --> RUNNER

    BENCH --> LOADER
    LOADER --> RUNNER
    RUNNER --> ADAPTER
    RUNNER --> TOOLS
    ADAPTER --> TOOLS
    RUNNER --> SCORERS
    RUNNER --> WRITER
    WRITER --> TRACE
    WRITER --> RESULT
    REP --> SUMMARY
```

---

## 2. Execution Flow (Single Task Run)

```mermaid
flowchart TD
    A([CLI: exabench run task]) --> B[BenchmarkRunner.run]

    B --> C1[TaskLoader.load_task\ntask_id → TaskSpec]
    B --> C2[EnvironmentLoader.load_environment\nenv_id → EnvironmentBundle]

    C1 --> D[Build ToolRegistry\nfor role + allowed_tools]
    C2 --> D

    D --> E[ExecutionContext\ntask + env + tools + run_id]

    E --> F{Adapter}

    subgraph FA["DirectQAAdapter"]
        F1[Return placeholder answer\nno tool calls]
    end

    subgraph OA["OpenAIAdapter"]
        O1[Build system prompt\n+ tool schemas] --> O2[LLM API call]
        O2 --> O3{tool_calls\nin response?}
        O3 -- yes --> O4[ToolRegistry.call\ntool_name · method · args]
        O4 --> O5[Append TraceStep\ntool_call + observation]
        O5 --> O2
        O3 -- no / max rounds --> O6[Extract final_answer]
    end

    F -- direct_qa --> FA
    F -- openai --> OA

    FA --> G[Trace]
    OA --> G

    G --> H[TraceWriter.write_trace\n→ traces/<task_id>_trace.json]

    G --> I[AggregateScorer.score]

    subgraph SCORE["Scoring Dimensions"]
        S1[OutcomeScorer\nexact / semantic / numeric]
        S2[ToolUseScorer\ncoverage · precision · redundancy]
        S3[GroundingScorer\ntoken overlap]
        S4[GovernanceScorer\npermission violations]
        S5[EfficiencyScorer\nstep count penalty]
        S6[RobustnessScorer\nscore variance]
    end

    I --> S1 & S2 & S3 & S4 & S5 & S6
    S1 & S2 & S3 & S4 & S5 & S6 --> W[Weighted Aggregate\nper scoring_profiles.yaml]

    W --> R[BenchmarkResult\naggregate_score + DimensionScores]
    R --> J[TraceWriter.write_result\n→ results/<task_id>_result.json]

    J --> K([Return BenchmarkResult])
```

---

## 3. Component Architecture

```mermaid
graph LR
    subgraph Schemas["schemas/"]
        TS[TaskSpec]
        ES[EnvironmentBundle]
        TR[Trace + TraceStep]
        TC[ToolCall + Observation]
        BR[BenchmarkResult\nDimensionScores]
        SC[ScoringConfig\nWeightProfile]
    end

    subgraph Loaders["loaders/"]
        TL[TaskLoader]
        EL[EnvironmentLoader]
        REG[BenchmarkRegistry]
    end

    subgraph Adapters["adapters/"]
        BA[BaseAdapter]
        DQA[DirectQAAdapter]
        OAI[OpenAIAdapter]
    end

    subgraph Runners["runners/"]
        CTX[ExecutionContext]
        RUN[BenchmarkRunner]
        TW[TraceWriter]
    end

    subgraph Tools["tools/"]
        BT[BaseTool]
        SL[MockSlurmTool\nquery_jobs · job_details\nlist_nodes · list_partitions]
        DO[MockDocsTool\nretrieve · list_docs]
        RB[MockRBACTool\ncheck · list_permissions]
        TE[MockTelemetryTool\nquery_memory_events · list_metrics]
        FA[MockFacilityTool\nquery_node_power · query_cluster_energy\nquery_rack_telemetry · list_inventory]
        TR2[ToolRegistry\nenforce allowed_tools]
    end

    subgraph Scorers["scorers/"]
        BS[BaseScorer]
        OS[OutcomeScorer]
        TUS[ToolUseScorer]
        GRS[GroundingScorer]
        GOS[GovernanceScorer]
        EFS[EfficiencyScorer]
        RBS[RobustnessScorer]
        AGG[AggregateScorer]
    end

    subgraph Reports["reports/"]
        JR[JsonReport]
        HR[HtmlReport]
        SL2[Slices\nrole × category matrix]
    end

    TL --> TS
    EL --> ES
    REG --> TL & EL

    BA --> DQA & OAI
    BT --> SL & DO & RB & TE & FA
    SL & DO & RB & TE & FA --> TR2

    RUN --> REG
    RUN --> CTX
    RUN --> TR2
    CTX --> BA
    BA --> TR
    TR --> TW
    TR --> AGG

    BS --> OS & TUS & GRS & GOS & EFS & RBS
    OS & TUS & GRS & GOS & EFS & RBS --> AGG
    AGG --> BR
    BR --> TW

    TW --> JR & HR & SL2
```

---

## 4. Environment Snapshot Structure

```mermaid
graph TD
    subgraph ENV["benchmark/environments/env_NN/"]
        META["metadata.yaml\nenv_id · snapshot · cluster\nroles · categories · status"]
        SLURM["slurm/\nslurm_state.json\njob_details.json"]
        TELEM["telemetry/\nmemory_events.csv\ntelemetry_timeseries.parquet"]
        DOCS["docs/\n*.md — HPC documentation"]
        POL["policy/\nrbac_policy.yaml"]
        INC["incidents/\nincident_metadata.json"]
        POWER["power/\nnode_power.csv\nrack_telemetry.csv\ninventory.json"]
    end

    META --> ENV_BUNDLE[EnvironmentBundle]
    SLURM --> MockSlurmTool
    TELEM --> MockTelemetryTool
    DOCS --> MockDocsTool
    POL --> MockRBACTool
    POWER --> MockFacilityTool
```

---

## 5. Scoring Pipeline

```mermaid
flowchart LR
    T[Trace] --> OS
    T --> TUS
    T --> GRS
    T --> GOS
    T --> EFS

    TASK[TaskSpec\ngold_answer\ngold_evidence_refs\nhard_fail_conditions] --> OS & TUS & GRS & GOS

    OS["OutcomeScorer\nexact_match\nsemantic_match\nnumeric\n→ 0–1"] --> AGG
    TUS["ToolUseScorer\ncoverage\nprecision\nno-redundancy\n→ 0–1"] --> AGG
    GRS["GroundingScorer\ntoken overlap\nobs vs answer\n→ 0–1"] --> AGG
    GOS["GovernanceScorer\npermission violations\n-0.25 per violation\n→ 0–1"] --> AGG
    EFS["EfficiencyScorer\nstep count linear\n≤5 → 1.0, ≥20 → 0.0\n→ 0–1"] --> AGG

    PROFILE["WeightProfile\n(scoring_profiles.yaml)\ndefault_hpc_v01\nalpha1_grounding\nalpha0_minimal"] --> AGG

    AGG["AggregateScorer\nweighted sum\nhard-fail check"] --> BR

    BR["BenchmarkResult\naggregate_score\nDimensionScores\nhard_fail"]
```

---

## 6. Role-Based Access Control Flow

```mermaid
flowchart TD
    TASK[TaskSpec\nrole: scientific_user\nallowed_tools: slurm · docs · telemetry] --> RUN[BenchmarkRunner]

    RUN --> TR2[ToolRegistry\nfiltered to allowed_tools]

    TR2 --> CALL{Tool Call}

    CALL -- "slurm.query_jobs()" --> SLURM[MockSlurmTool]
    CALL -- "docs.retrieve()" --> DOCS[MockDocsTool]
    CALL -- "facility.query_power()" --> DENY[ToolResult\npermission_denied=True]

    SLURM --> RBAC{Role Check}
    RBAC -- "scientific_user\n→ own jobs only" --> OWN[Filtered results\nown user's jobs]
    RBAC -- "sysadmin\n→ all jobs" --> ALL[All job results]

    DENY --> GOS[GovernanceScorer\npenalize violation]
    OWN --> TRACE[TraceStep observation]
    ALL --> TRACE
```

---

## 7. CLI Command Map

```mermaid
graph TD
    CLI([exabench]) --> RUN[run]
    CLI --> VAL[validate]
    CLI --> REP[report]
    CLI --> CMP[compare]
    CLI --> ROB[robustness]

    RUN --> RT["run task\n--task ID --env ID\n--adapter direct_qa|openai:gpt-4o"]
    RUN --> RA["run all\n--adapter NAME"]

    VAL --> VB["validate benchmark\n--benchmark DIR"]

    REP --> RJ["report json RUN_DIR\n→ run_summary.json"]
    REP --> RH["report html RUN_DIR\n→ report.html"]
    REP --> RS["report slices RUN_DIR\n→ role×category table"]

    CMP --> CR["compare runs RUN_A RUN_B\n→ diff JSON"]

    ROB --> RBT["robustness task\n--task ID --env ID\n--adapter NAME --n N\n→ mean · std · robustness_score"]
```
