
# 🧠 HPC Normal Users (Application Users / Scientists / Engineers)

## **Primary Mission**
- Efficiently run computational workloads and scientific simulations on HPC systems.
- Manage data, optimize performance, and ensure successful job execution.
- Utilize available HPC software environments for research and engineering tasks.

## **Core Tasks & Responsibilities**
- Submit, monitor, and manage batch or interactive jobs.
- Handle input/output datasets and organize project directories.
- Configure and load required software modules and environments.
- Debug failed jobs and analyze performance bottlenecks.
- Manage storage quotas and data transfers.
- Use GPUs and accelerators effectively for computation.
- Collaborate on shared HPC projects and manage access permissions.
- Follow documentation and tutorials to learn best practices.

## **Key Studies / Knowledge Areas**
- Linux shell and job schedulers (e.g., SLURM, PBS).
- Parallel programming concepts (MPI, OpenMP, CUDA).
- Scientific software stack and module systems.
- Data management on distributed file systems (Lustre, GPFS).
- Job profiling and performance tuning.
- GPU utilization and accelerator performance.
- Monitoring and interpreting HPC telemetry (CPU, memory, thermal, etc.).

## **Data Sources They Analyze**
- Job scheduler logs and accounting data.
- Output/error files from simulations.
- Monitoring telemetry (CPU, GPU, memory, temperature).
- Storage usage and quota statistics.
- SLURM and system status dashboards.

## **Tools & Frameworks**
- SLURM, PBS, or LSF job schedulers.
- HPC module system, Conda, virtualenv.
- JupyterHub, interactive shell tools.
- HPC monitoring/Grafana dashboards.
- File transfer tools (scp, rsync, Globus).
- Profiling tools (nvprof, perf, gprof).
- RAG Agent for documentation queries.
- ExaSage and Facility Agents for runtime and environmental monitoring.

## **Research Themes / Study Topics**
- Job execution and runtime optimization.
- Application scaling and parallel efficiency.
- Resource utilization and queue management.
- Workflow automation and scheduling policies.
- Energy-aware computing and sustainability.
- Debugging and reliability enhancement.
- Data management and reproducibility.
- User experience improvement via AI-driven assistants.

---

## **Example Queries for Multi-Agentic Chat System**

| # | Code | Category | Description | Example Queries | Priority |
|---|------|-----------|--------------|-----------------|-----------|
| 1 | **JOB** | **Job Submission & Management** | Submit, cancel, or resubmit jobs through schedulers. | “Submit my script with 4 GPUs.”<br>“Cancel job 102345.” | **H** |
| 2 | **QUEUE** | **Queue & Resource Status** | View queues, waiting times, and node assignments. | “Which queue has the shortest wait?”<br>“Show my running jobs.” | **H** |
| 3 | **DATA** | **Data Management & File Operations** | Manage input/output data, clean directories, and perform transfers. | “Copy data to scratch.”<br>“Delete old files older than 30 days.” | **H** |
| 4 | **SOFT** | **Software Modules & Environment Setup** | Load or configure scientific software environments. | “Load Python 3.10 with TensorFlow.”<br>“List available modules.” | **H** |
| 5 | **PERF** | **Performance Optimization** | Investigate runtime inefficiencies and recommend tuning actions. | “Why is my job slow?”<br>“Show CPU/GPU utilization for job 54321.” | **M** |
| 6 | **DEBUG** | **Troubleshooting & Debugging** | Diagnose job failures or software errors. | “Why did my job fail?”<br>“Explain MPI rank error.” | **H** |
| 7 | **GPU** | **GPU & Accelerator Usage** | Request or monitor GPU utilization and performance. | “Request 2 GPUs for my next job.”<br>“Check GPU temperature.” | **M** |
| 8 | **STOR** | **Storage & Quota Management** | Manage storage usage and request additional quota. | “How much storage am I using?”<br>“List my largest files.” | **M** |
| 9 | **INTER** | **Interactive & Jupyter Workflows** | Launch interactive sessions or notebooks. | “Launch Jupyter session.”<br>“Start interactive job on GPU node.” | **M** |
| 10 | **DOCS** | **Documentation & Learning Assistance** | Retrieve examples, tutorials, and guidance. | “How to use Python with MPI?”<br>“Find example SLURM script.” | **H** |
| 11 | **COLL** | **Collaboration & Project Sharing** | Manage shared projects, permissions, and collaboration. | “Share folder with my project group.”<br>“Invite collaborator to project.” | **M** |
| 12 | **MON** | **Monitoring & Runtime Metrics** | Query system or job metrics for analysis. | “Show CPU usage for my last job.”<br>“Plot memory usage trend.” | **M** |
| 13 | **AUTO** | **Workflow Automation & Scripting** | Automate job submission or file-triggered workflows. | “Schedule daily job submission.”<br>“Trigger workflow when dataset changes.” | **L** |
| 14 | **SEC** | **Security & Access Management** | Manage authentication and permissions. | “Add my SSH key.”<br>“Reset my HPC password.” | **L** |
| 15 | **ENERGY** | **Facility Awareness & Energy Efficiency** | View sustainability and facility metrics. | “What’s the PUE today?”<br>“View cluster energy trends.” | **L** |

---

## **Priority Tags Summary**

| Priority | Meaning | Categories |
|----------|----------|------------|
| **H (High)** | Frequent, essential for daily workflow | JOB, QUEUE, DATA, SOFT, DEBUG, DOCS |
| **M (Medium)** | Regular but situational needs | PERF, GPU, STOR, INTER, COLL, MON |
| **L (Low)** | Occasional, admin-assisted, or advanced | AUTO, SEC, ENERGY |

---

<!-- Version: 1.0 — Generated 2025-10-31 -->
