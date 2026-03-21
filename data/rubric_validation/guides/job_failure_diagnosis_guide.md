# Plain-Language Rubric Guide: `hpc_job_failure_diagnosis_v1`

**Version:** pre-annotation draft (update after calibration Round 1)
**Rubric template:** `hpc_job_failure_diagnosis_v1`
**Dimensions:** `technical_correctness` (0–3), `role_appropriateness` (0–2), `actionability` (0–2)

---

## 1. Dimension Definitions

### `technical_correctness` (0–3)

Does the response identify the correct root cause and cite explicit evidence from the SLURM accounting data?

| Score | Meaning |
|-------|---------|
| 0 | Wrong root cause, or no cause identified, or hallucinated metrics not in context |
| 1 | Correct cause category identified but no evidence cited (vague e.g. "it seems like memory") |
| 2 | Correct cause + at least one explicit evidence item from sacct (e.g. MaxRSS, ExitCode, Elapsed, Timelimit) |
| 3 | Correct cause + multiple explicit evidence items + correctly distinguishes from alternative causes |

**What counts as evidence in SLURM context:**
- Explicit sacct field values: `ExitCode=137`, `MaxRSS=63.9GB`, `Elapsed=72:00:00`, `Timelimit=72:00:00`
- Stderr text quoted verbatim: `"slurmstepd: error: Exceeded job memory limit"`
- Dependency state values: `afterok:1050099 (State=FAILED)`

**What does NOT count as evidence:**
- Vague claims: "the job may have run out of memory" (without citing MaxRSS)
- Plausible but unverifiable assertions: "RSS was 98.3% of limit" when only "~64GB" was stated
- General HPC knowledge not grounded in the specific context snippet

**Tie-breaking rule:** If the agent mentions the correct cause but the evidence is only implicit ("the job was killed by the OOM killer" without citing ExitCode=137 or the MaxRSS value), score `technical_correctness` = 1, not 2.

---

### `role_appropriateness` (0–2)

Is the response calibrated to the user's role as stated in the task context?

| Score | Meaning |
|-------|---------|
| 0 | Ignores role constraints, or provides information/actions beyond what the stated role can access |
| 1 | Acknowledges role but provides generic advice not specific to the stated role's capabilities |
| 2 | Response is clearly tailored to the stated role: correct partition names, permission levels, escalation paths |

**Examples:**
- **standard_user** responses should reference user-accessible commands (`sacct --user=$USER`, `--mem` flag in job script) and note when escalation (e.g., highmem partition PI request) is needed.
- **power_user** responses may include more advanced diagnostics (profiling, RAPL power caps) without requiring PI approval for standard quota increases.
- If no role is specified in the context, score 1 if advice is reasonable for a typical user, 2 if advice explicitly covers multiple role paths.

---

### `actionability` (0–2)

Does the response provide specific, safe, correctly sequenced remediation steps?

| Score | Meaning |
|-------|---------|
| 0 | No steps given, or steps are generic/vague ("try resubmitting"), or steps are potentially harmful |
| 1 | Some concrete steps given but incomplete (missing key command, wrong order, or not addressing root cause) |
| 2 | Complete, specific, correctly sequenced steps that directly address the diagnosed root cause |

**Specificity requirement:** "Increase memory" is not specific. "#SBATCH --mem=128G" is specific. The distinction is whether a user can execute the step exactly as written.

---

## 2. `path_chosen` Field

Record which solution path you matched:
- `resource_exhaustion` — failure caused by exceeding memory, CPU time, or walltime limits
- `dependency_failure` — failure caused by an upstream dependency job failing
- `other` — neither of the above (application bug, missing file, module mismatch, etc.)

---

## 3. Worked Examples

### Example A — POOR (score: 0, 0, 0)

**Context:** Job 1047321 failed, ExitCode=137, MaxRSS=48.2GB, ReqMem=32GB
**Response:** "The job failed. This might be because the cluster was busy. Try resubmitting."

- `technical_correctness=0`: No root cause identified; ignores ExitCode=137 and MaxRSS > ReqMem
- `role_appropriateness=0`: No role context considered
- `actionability=0`: "Try resubmitting" does not address the root cause

---

### Example B — MODERATE (score: 2, 1, 1)

**Context:** Same as above
**Response:** "Job 1047321 appears to have failed due to exceeding its memory limit. The MaxRSS of 48.2GB exceeds the 32GB requested. The user should increase the memory request, perhaps to 96GB."

- `technical_correctness=2`: Correct cause (OOM), cites MaxRSS=48.2GB and ReqMem=32GB
- `role_appropriateness=1`: Generic advice, no role-specific guidance
- `actionability=1`: "96GB" is a specific value but no SBATCH syntax; incomplete escalation path
- `path_chosen`: resource_exhaustion

---

### Example C — GOOD (score: 3, 2, 2)

**Context:** Same as above. User role: standard_user.
**Response:** "Root cause: OOM. ExitCode=137 (SIGKILL by kernel OOM killer), MaxRSS=48.2GB exceeds ReqMem=32GB. Fix: add #SBATCH --mem=64G to your job script. If 64GB is insufficient, the standard partition allows up to 128GB; requests above that require PI authorization for the highmem partition."

- `technical_correctness=3`: Correct cause, cites ExitCode=137 AND MaxRSS AND ReqMem, distinguishes SIGKILL from SIGTERM
- `role_appropriateness=2`: Correctly states standard partition limit and escalation path for standard_user
- `actionability=2`: Exact SBATCH flag given, correctly sequenced (fix script → if not enough → escalate)
- `path_chosen`: resource_exhaustion
