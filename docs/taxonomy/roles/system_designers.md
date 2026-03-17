# 🧠 HPC System Designers / Architects

## **Primary Mission**
- Architect scalable, energy-efficient, reliable HPC systems by integrating compute, network, storage, and facility constraints, and validating performance, cost, and sustainability targets. 

## **Core Tasks & Responsibilities**
- Define node mix, rack topology, and interconnect hierarchy.
- Size hardware (CPU/GPU, memory, accelerators) against workload profiles.
- Design and validate network/fabric architectures (IB/Ethernet/NVLink).
- Plan storage/I/O subsystems (Lustre/BeeGFS/Ceph) and throughput targets.
- Model performance/efficiency; run benchmarks and scalability tests.
- Specify monitoring/telemetry granularity and alerting strategy.
- Assess reliability/availability (RAM), failure trends, and resilience.
- Perform CAPEX/OPEX/TCO analyses and procurement trade-off studies.

## **Key Studies / Knowledge Areas**
- System architecture & capacity planning; topology-aware design.
- Interconnect theory (fat-tree, dragonfly), latency/bisection modeling.
- Energy efficiency & thermal modeling; PUE and cooling strategies.
- Parallel storage & I/O stack design; NVMe vs HDD trade-offs.
- Performance modeling, benchmarking methodology, scalability analysis.
- RAM (reliability/availability/maintainability) & operational risk.
- Security, RBAC, multi-tenancy, and network isolation patterns.
- Documentation & standards alignment (ISO/IEC, best practices).

## **Data Sources They Analyze**
- Node/cluster telemetry (IPMI, GPU/CPU metrics), network counters, IB port errors.
- Facility/DCIM data (power density, cooling zones, environmental maps).
- Storage/I/O stats; benchmark results (STREAM, LINPACK) and job traces.
- Procurement/warranty inventories; cost and lifecycle datasets.

## **Tools & Frameworks**
- Monitoring & analytics agents (ExaSage, Facility Agent, Data Analytics, Simulation).
- Scheduler & benchmarking toolchains (e.g., SLURM, STREAM, HPL/LINPACK).
- Storage stacks (Lustre, BeeGFS, Ceph) and topology visualization utilities.
- RAG/knowledge agents for documentation/standards and design reports.

## **Research Themes / Study Topics**
- Architecture/topology planning for mixed CPU–GPU workloads.
- Performance-per-watt optimization; cooling strategy comparison.
- Interconnect scalability and congestion modeling.
- Storage/I/O throughput optimization and cost efficiency.
- Reliability/failure trend analysis and resilience planning.
- Monitoring/observability design (metrics selection, alerts).
- Sustainability & lifecycle (refresh planning, CO₂ footprint).
- Benchmarking/validation protocols and acceptance testing.

---

## **Example Queries for Multi-Agentic Chat System**

| # | Code | Category | Description | Example Queries | Priority |
|---|------|-----------|--------------|-----------------|-----------|
| 1 | **JOB** | **Job & Workflow Management** | Designers trigger validation runs and define scheduler partitions to test design assumptions. | “Run STREAM and report memory bandwidth per node.”<br>“Suggest scheduler partitioning for hybrid CPU–GPU workloads.” | **M** |
| 2 | **PERF** | **Performance & Optimization** | Model and validate expected performance; build baselines and scaling curves. | “Estimate LINPACK performance scaling for 512 nodes.”<br>“Generate a performance baseline report for the new node configuration.” | **H** |
| 3 | **DATA** | **Data & Storage Management** | Plan parallel file systems and I/O topology; evaluate capacity and cost. | “Which configuration yields the best I/O throughput for 5 PB of scratch storage?”<br>“Compare NVMe vs HDD for cost per TB.” | **M** |
| 4 | **MON** | **Monitoring & Observability** | Specify telemetry granularity and fault/thermal monitoring strategy. | “Which sensors should be monitored via IPMI?”<br>“How to set up monitoring for InfiniBand port errors?” | **H** |
| 5 | **ENERGY** | **Power, Energy & Sustainability** | Optimize energy efficiency and cooling; analyze PUE and thermal hotspots. | “Show energy-efficiency curves under 80% load.”<br>“Compare the energy efficiency of liquid vs air cooling.” | **H** |
| 6 | **FAC** | **Facility, Infrastructure & Environmental Systems** | Map compute to room constraints; power density and cooling-zone balance. | “How should I distribute racks to balance cooling zones?”<br>“Show the current rack power density map.” | **M** |
| 7 | **SEC** | **Security, Access & Policy Management** | Define RBAC, multi-tenancy, and network isolation for shared infra. | “How to isolate network for different research groups?”<br>“Recommend an RBAC model for shared infrastructure.” | **M** |
| 8 | **ARCH** | **System Architecture, Design & Capacity Planning** | Choose node mix, rack counts, and topology aligned to workloads. | “What is the optimal CPU–GPU ratio for mixed AI and CFD workloads?”<br>“How many racks do I need for 1000 dual-socket nodes?” | **H** |
| 9 | **AIOPS** | **AI, Automation & Intelligent Operations** | Use analytics/ML to predict hotspots, failures, or obsolescence. | “Predict thermal hotspots using IPMI + facility data.”<br>“Predict hardware obsolescence timeline based on warranty data.” | **M** |
| 10 | **DOCS** | **Documentation, Support & Knowledge Assistance** | Surface standards/best practices; generate architecture deliverables. | “Show ISO/IEC guidelines relevant to HPC datacenter design.”<br>“Generate architecture documentation for a funding proposal.” | **M** |

---

## **Priority Tags Summary**

| Priority | Meaning | Categories |
|----------|----------|------------|
| **H (High)** | Frequent, critical for design validation and day-to-day planning | **PERF**, **MON**, **ENERGY**, **ARCH** |
| **M (Medium)** | Periodic or situational needs | **JOB**, **DATA**, **FAC**, **SEC**, **AIOPS**, **DOCS** |
| **L (Low)** | Rare but high-value or admin-only needs | (None specific beyond long-term sustainability/lifecycle reviews) |
