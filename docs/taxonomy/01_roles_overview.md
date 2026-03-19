# 01 — Roles & Personas

Owner: Mohsen

### Purpose of this dimension

This section defines **who is asking** in an ExaBench task, what that persona typically cares about, what information and tools they can normally access, and what a representative task looks like.

---

### Persona list

| Schema value | Role | Detail page |
|---|---|---|
| `sysadmin` | System Administrator | [system_administrators.md](roles/system_administrators.md) |
| `facility_admin` | Facility Admin / Technicians | [facility_admin.md](roles/facility_admin.md) |
| `researcher` | HPC Researcher / Analyst | [researchers.md](roles/researchers.md) |
| `scientific_user` | Normal User (Scientist / Engineer) | [normal_users.md](roles/normal_users.md) |
| `system_designer` | System Designer / Architect | [system_designers.md](roles/system_designers.md) |

---

### Short definition per persona

- **System administrator**: keeps the cluster reliable, secure, and performant. Works with schedulers, nodes, storage, and security.
- **Facility operator / admin**: keeps datacenter power and cooling safe and stable. Works with BMS/DCIM, alarms, and energy KPIs.
- **Researcher**: analyzes telemetry and traces to understand performance, failures, and efficiency. Focuses on experiments and analytics.
- **Normal user**: runs workloads and needs help submitting jobs, debugging failures, and managing data and environments.
- **System designer / architect**: plans system topology and capacity. Balances performance, cost, reliability, and energy.

---

### Typical goals

- Get an accurate answer fast, at the right level of detail for the persona.
- Make the right operational decision (mitigate incident, optimize, plan capacity, or complete a workflow).
- Avoid unsafe actions and avoid exposing sensitive data.

---

### Allowed information scope (high-level)

- **User-facing (normal user)**: own jobs and allocations, public docs, safe how-to guidance.
- **Researcher**: aggregated or anonymized telemetry, historical traces, approved datasets, plus docs.
- **SysAdmin**: node-level metrics, logs, queue controls, user/group info, configuration context.
- **Facility**: facility telemetry, alarms, setpoints, energy and cooling controls (often restricted to read-only unless explicitly authorized).
- **Architect**: aggregated fleet telemetry, benchmark results, procurement and inventory summaries (as permitted), design docs.

---

### Example queries

These are representative prompts; the detailed lists live in each persona page.

- **Normal user**: “Why did my last job fail and how can I fix it?”
- **Researcher**: “Correlate node power consumption with CPU load for the last month.”
- **SysAdmin**: “List nodes with repeated GPU ECC errors and suggest next checks.”
- **Facility**: “Which racks exceeded 28 °C inlet temperature today?”
- **Architect**: “Estimate performance-per-watt impact of switching to liquid cooling for GPU racks.”

# HPC User Personas & Capability Matrix


| User Type                                 | Primary Mission                                                                                   | Top Responsibilities (condensed)                                                                                             | Key Data Sources                                                                                  | Typical Tools                                                                        | **High-Priority Categories (Codes)** | Example High-Priority Query                                            |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------ | ---------------------------------------------------------------------- |
| **Facility Admin / Technicians**          | Ensure safe, reliable, and energy-efficient operation of HPC datacenter power and cooling systems | Monitor environmental metrics; manage CRAC/RDHX/chillers; track energy/PUE; handle alarms; maintenance and safety compliance | BMS/DCIM telemetry, IPMI/Redfish, PDU/UPS/CRAC meters, facility logs, CO₂ reports                 | HPC monitoring/Grafana, BMS/DCIM tools (SNMP/Redfish), Python automation, RAG for SOPs   | **MON, ENERGY, FAC, AIOPS, DOCS**    | “List all **active critical alarms** and show affected racks.”         |
| **Normal Users (Scientists / Engineers)** | Run computational workloads efficiently and manage research data                                  | Submit & monitor jobs, manage data, configure environments, debug failures, optimize performance                             | Scheduler logs, job outputs, CPU/GPU telemetry, storage usage                                     | SLURM/PBS, Modules/Conda, JupyterHub, Profilers, RAG Docs                            | **JOB, DATA, PERF, MON, DOCS**       | “**Submit** my SLURM job with 4 GPUs and 64 GB RAM.”                   |
| **System Administrators**                 | Maintain reliability, performance, and security of HPC clusters                                   | Manage users/RBAC, monitor nodes, control queues, maintain OS/firmware, ensure compliance, automate tasks                    | Node/job metrics, scheduler logs, syslogs, storage telemetry, IPMI/BMS data, security logs        | SLURM, HPC monitoring/Grafana/ELK, IPMI/Redfish, Ansible/Terraform, Spack, Lustre/BeeGFS | **JOB, MON, DATA, SEC, AIOPS**       | “**Drain** node n101 and requeue pending jobs.”                        |
| **System Designers / Architects**         | Architect scalable, efficient HPC systems across compute, storage, and facility layers            | Define node mix and topology; plan interconnects and storage; run benchmarks; analyze efficiency and cost                    | IPMI/GPU/CPU telemetry, IB counters, PUE maps, benchmark results, procurement data                | Benchmark suites (HPL/STREAM), Topology tools, RAG for standards                     | **ARCH, PERF, ENERGY, MON, DOCS**    | “Estimate **LINPACK scaling** for 512 nodes and identify bottlenecks.” |
| **HPC Researchers / Analysts**            | Analyze and model system performance, energy, and reliability using data-driven methods           | Build ML models for anomalies; analyze logs & telemetry; estimate energy; correlate compute vs facility data                 | HPC monitoring/InfluxDB/PostgreSQL, parquet exports, SLURM logs, RAPL/IPMI data, facility telemetry | Pandas/Dask, PyTorch/TensorFlow, HPCToolkit, Grafana, MLflow/DVC                     | **AIOPS, PERF, ENERGY, DATA, MON**   | “**Detect** power anomalies across 3 years and rank top outlier jobs.” |


