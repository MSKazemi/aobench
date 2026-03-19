# 🧠 HPC System Administrators

## **Primary Mission**
- Ensure reliability, performance, and security of large-scale HPC clusters.
- Manage compute, storage, and network infrastructure supporting scientific workloads.
- Maintain job schedulers, user access, and system health across heterogeneous hardware.
- Enable smooth coordination between compute systems, facility environments, and AIOps agents.

---

## **Core Tasks & Responsibilities**
- Manage user accounts, permissions, and access policies (LDAP, SSH, groups).
- Monitor and maintain compute nodes, GPUs, interconnects, and storage systems.
- Oversee job scheduling, queue control, and resource allocation (SLURM/PBS).
- Troubleshoot performance degradation and system failures.
- Maintain OS images, firmware, and configuration management.
- Track energy, power, and cooling parameters for operational sustainability.
- Ensure system compliance, backups, and data protection.
- Support automation, scripting, and AI-based observability tools.

---

## **Key Studies / Knowledge Areas**
- HPC job schedulers (SLURM, PBS, LSF)
- Parallel computing and MPI/OpenMP behavior
- Linux system administration and shell scripting
- Cluster monitoring, telemetry, and alerting (HPC monitoring tools, Grafana)
- File systems (Lustre, BeeGFS, Ceph, NFS)
- Networking and InfiniBand diagnostics
- Security and compliance frameworks (CIS, ISO, GDPR)
- Configuration and automation tools (Ansible, Terraform)
- Power management, IPMI, and node telemetry analytics

---

## **Data Sources They Analyze**
- Node and job metrics (CPU, GPU, I/O, memory, network)
- Scheduler logs and accounting data
- System and kernel logs (syslog, dmesg)
- Storage and filesystem telemetry (OST, MDT statistics)
- Facility data (IPMI, PDU, CRAC, BMS telemetry)
- Security and authentication logs
- User activity and quota databases

---

## **Tools & Frameworks**
- SLURM / PBS / LSF job schedulers  
- HPC monitoring tools (Grafana, Elastic Stack, InfluxDB)
- IPMI, Redfish, SNMP, DCIM systems  
- Ansible, Terraform, Spack, Singularity, Docker  
- Lustre / BeeGFS / Ceph / NFS file systems  
- Python, Bash, PowerShell for automation  
- ExaSage, KubeIntellect, ThermADNet for AI-driven observability  
- Monitoring dashboards, REST APIs, and alerting systems

---

## **Research Themes / Study Topics**
- Cluster performance optimization and utilization efficiency
- Predictive maintenance and fault detection
- Energy- and thermal-aware operations
- Job scheduling fairness and resource balancing
- Automation of provisioning and configuration management
- Integration of AI/LLM agents for intelligent operations
- Compliance, security audits, and access governance
- Resilience, recovery, and disaster preparedness

---

## **Example Queries for Multi-Agentic Chat System**

| # | Code | Category | Description | Example Queries | Priority |
|---|------|-----------|--------------|-----------------|-----------|
| 1 | **JOB** | **Job & Workflow Management** | Manage queues, monitor job states, reprioritize workloads. | “Pause queue gpu_long.”<br>“Cancel all jobs from user test.” | **H** |
| 2 | **RES** | **Cluster Resource Management** | Control compute/GPU/storage resources and partitions. | “Show node allocation per partition.”<br>“Drain node n101.” | **H** |
| 3 | **USER** | **User & Access Management** | Manage accounts, groups, and privileges. | “Add user alice to group decice.”<br>“List inactive users.” | **H** |
| 4 | **MON** | **Monitoring & Health Status** | Observe system state, detect failures, visualize trends. | “Show failed nodes in last 24h.”<br>“Check GPU utilization trends.” | **H** |
| 5 | **PERF** | **Performance & Utilization Analysis** | Analyze efficiency, CPU/GPU load, I/O, and bottlenecks. | “Top 10 users by CPU usage.”<br>“Detect underutilized nodes.” | **H** |
| 6 | **STOR** | **Data & Storage Management** | Manage file systems, quotas, and I/O performance. | “Show OST usage by project.”<br>“Check I/O throughput per user.” | **H** |
| 7 | **NET** | **Network & Interconnect Diagnostics** | Inspect InfiniBand/Fabric status and connectivity. | “List ports with packet drops.”<br>“Show latency per switch.” | **M** |
| 8 | **SEC** | **Security & Compliance** | Audit access, check vulnerabilities, apply security policies. | “Audit sudo access.”<br>“List failed login attempts.” | **H** |
| 9 | **SWENV** | **Software Environment & Modules** | Manage modules, containers, compilers, and Spack builds. | “List loaded modules for user bob.”<br>“Add new module OpenMPI 5.0.” | **H** |
| 10 | **NODE** | **Node Maintenance & Lifecycle** | Provision, reboot, or decommission compute nodes. | “Reboot node n102.”<br>“Mark node n108 as maintenance.” | **H** |
| 11 | **ENERGY** | **Power, Energy & Thermal Management** | Track energy efficiency and temperature conditions. | “Average rack power for R5.”<br>“Detect overheating nodes.” | **M** |
| 12 | **FAC** | **Facility & Infrastructure Awareness** | Integrate facility data: racks, PDUs, zones, sensors. | “Show spatial layout of racks in room A.”<br>“Which racks share PDU B4?” | **M** |
| 13 | **BACKUP** | **Backup & Disaster Recovery** | Manage data snapshots and recovery operations. | “Check backup status for /home.”<br>“Restore /projects/decice.” | **L** |
| 14 | **AUTO** | **Automation & Scripting Assistance** | Generate scripts and automate routine admin tasks. | “Generate SLURM restart script.”<br>“Automate GPU utilization report.” | **H** |
| 15 | **LOGS** | **Logs, Alerts & Troubleshooting** | Query logs and alert streams for failures or anomalies. | “Show dmesg logs for node n107.”<br>“Which jobs failed due to OOM?” | **H** |
| 16 | **DOCS** | **Documentation & Admin Support** | Retrieve SOPs, manuals, and wiki procedures. | “How to reset a failed SLURM node?”<br>“Procedure to replace GPU.” | **M** |
| 17 | **API** | **Integration & API Management** | Manage HPC monitoring/Grafana endpoints, webhooks, APIs. | “List all monitoring targets.”<br>”Check API token validity.” | **L** |
| 18 | **LIC** | **License & Quota Management** | Monitor license usage and enforce user quotas. | “Check ANSYS license usage.”<br>“Set 10TB quota for project UC3.” | **M** |
| 19 | **AIOPS** | **AI & Intelligent Operations** | Manage and validate AI/LLM agents and policy integration. | “Limit monitoring data to admins.”<br>“Review LLM privacy policy.” | **L** |
| 20 | **SUPPORT** | **User Support & Incident Response** | Handle incidents, tickets, and user notifications. | “List all open tickets.”<br>“Notify users about downtime.” | **H** |

---

## **Priority Tags Summary**

| Priority | Meaning | Categories |
|----------|----------|------------|
| **H (High)** | Frequent and critical operations | JOB, RES, USER, MON, PERF, STOR, SEC, SWENV, NODE, AUTO, LOGS, SUPPORT |
| **M (Medium)** | Important but periodic checks | NET, ENERGY, FAC, DOCS, LIC |
| **L (Low)** | Rare or specialized administrative actions | BACKUP, API, AIOPS |

---

## ✅ **Suggestions**
- Add **AIOps anomaly correlation** queries linking SLURM logs, telemetry, and temperature metrics.  
- Integrate **LLM policy guardrails** for high-risk operations (e.g., reboot, queue control).  
- Create **visual topology mapping** between racks and node pools to enhance facility queries.  
- Expand **energy dashboard integration** for carbon-aware scheduling.

---

<!-- Version: 1.1 — Improved by GPT-5 | 2025-10-31 -->
