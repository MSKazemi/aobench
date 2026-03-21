# Plain-Language Rubric Guide: `hpc_energy_anomaly_v1`

**Version:** pre-annotation draft (update after calibration Round 1)
**Rubric template:** `hpc_energy_anomaly_v1`
**Dimensions:** `technical_correctness` (0–3), `conciseness` (0–2), `actionability` (0–2)

---

## 1. Dimension Definitions

### `technical_correctness` (0–3)

Does the response correctly identify the mechanism causing the energy anomaly, grounded in the snapshot data?

| Score | Meaning |
|-------|---------|
| 0 | Wrong mechanism, or mechanism unrelated to the context, or hallucinated values |
| 1 | Plausible mechanism mentioned but not grounded in specific context values |
| 2 | Correct mechanism + at least one specific metric from context (power value, utilization %, temperature, job ID) |
| 3 | Correct mechanism + multiple metrics + rules out alternative explanations |

**Energy anomaly mechanisms in HPC context:**
1. **CPU/memory saturation** — workload entering compute-intensive phase; DVFS drives max voltage
2. **GPU runaway process** — orphaned process consuming GPU after job end
3. **Synchronized job array** — multiple jobs entering peak phase simultaneously
4. **Thermal-driven power increase** — temperature feedback loop (less common)
5. **Phase oscillation** — periodic compute/sync cycles in iterative solvers

**What counts as evidence:**
- Explicit power values: "820W" (not just "high power")
- Utilization percentages: "CPU at 98%", "GPU at 99%"
- Temperature readings: "89°C approaching 90°C warning threshold"
- Job IDs and states: "job 1047888 (MPI, 32 tasks)"
- Time correlation: "spikes coincide with job array start at 09:00 UTC"

**What does NOT count:**
- Vague mechanism without citing context: "the node is under heavy load"
- Hallucinated specifics: "the node is drawing 950W" when context says 820W
- General knowledge claims not tied to the specific snapshot

---

### `conciseness` (0–2)

Is the response operationally appropriate in length for an HPC operations context?

| Score | Meaning |
|-------|---------|
| 0 | Response is either far too brief (1–2 sentences with no actionable content) or excessively padded (>500 words for a straightforward anomaly) |
| 1 | Appropriate length but with unnecessary padding, repeated points, or irrelevant tangents |
| 2 | Tight, operator-appropriate length: covers the anomaly mechanism and mitigation without filler |

**Guidance:** HPC operators expect concise technical communication. A 3–5 paragraph response covering mechanism + evidence + mitigation is ideal for complex anomalies. A single-sentence response is insufficient. A 1000-word essay is excessive. Use your judgment calibrated to what an on-call operator would find useful.

---

### `actionability` (0–2)

Does the response recommend concrete mitigation steps appropriate to the anomaly type?

| Score | Meaning |
|-------|---------|
| 0 | No mitigation suggested, or mitigation is irrelevant (e.g., "restart the cluster") |
| 1 | Mitigation direction given but not actionable (e.g., "reduce power consumption") |
| 2 | Specific mitigation steps with commands, thresholds, or escalation paths |

**Note:** For some anomalies, the correct answer is "no action needed" (e.g., expected phase oscillation, expected compute peak). Score `actionability=2` if the response correctly identifies this and explains why. Score 0 if the response incorrectly recommends intervention for expected behavior.

---

## 2. Worked Examples

### Example A — POOR (score: 0, 0, 0)

**Context:** Node cn045, 820W power draw (2.4× baseline of 341W), CPU at 98%, memory bandwidth at 94%
**Response:** "The node is using too much power. Restarting the node should help."

- `technical_correctness=0`: No mechanism identified; "restart" is inappropriate
- `conciseness=0`: Too brief with no substantive content
- `actionability=0`: Restart would disrupt running jobs and is irrelevant to a workload-driven spike

---

### Example B — MODERATE (score: 2, 1, 1)

**Response:** "The 2.4× power spike on cn045 is likely caused by the running job entering a compute-intensive phase, driving CPU to 98% utilization and memory bandwidth to 94% of peak. The user should monitor the job and check if this is expected behavior."

- `technical_correctness=2`: Correct mechanism (saturation), cites CPU 98% and memory bandwidth 94%
- `conciseness=1`: Adequate length but "monitor and check" is weak
- `actionability=1`: "Monitor" is not specific; no RAPL/power cap command or threshold given

---

### Example C — GOOD (score: 3, 2, 2)

**Response:** "The 820W spike (2.4× baseline of 341W) is driven by CPU+memory saturation: 98% CPU utilization at max DVFS voltage combined with 94% memory bandwidth puts both subsystems in their highest-power state. This is a workload-phase transition, not a hardware fault. If the PDU budget allows, no action is needed. If a power cap is required, apply Intel RAPL at 650W: `powercap-set -z 0 -c 0 -p power_limit_uw 650000000`."

- `technical_correctness=3`: Correct mechanism (DVFS + memory saturation), cites both 820W and 341W baseline, correctly rules out hardware fault
- `conciseness=2`: Tight, operator-appropriate; covers mechanism + evidence + mitigation + decision point
- `actionability=2`: Specific RAPL command with exact wattage value; conditional framing (only if budget exceeded)
