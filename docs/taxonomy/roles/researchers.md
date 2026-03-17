# 🧠 HPC Researchers / Analysts

## **Primary Mission**                            
- Bridge scientific computing with data-driven optimization — analyze, model, and improve performance, energy efficiency, reliability, and sustainability across the entire HPC system stack.

## **Core Tasks & Responsibilities**
- Develop new parallel algorithms or machine learning models for HPC workloads.
- Perform anomaly detection on multi-year cluster monitoring datasets (thermal, power, performance, logs).
- Analyze system logs, scheduler traces, and job metadata to identify performance bottlenecks and failure patterns.
- Conduct power consumption estimation from job scripts and runtime telemetry (batch script → estimated Joules).
- Study long-term facility & IT data (cooling, temperature, power, humidity) to model correlations between compute load and energy usage.
- Perform operational data analysis for optimization and sustainability studies.

## **Key Studies / Knowledge Areas**
- HPC performance engineering (MPI, OpenMP, CUDA, SYCL)
- Anomaly detection & time-series analysis (ML/DL for logs & telemetry)
- Operational data analytics (Grafana/Prometheus data export, PostgreSQL, InfluxDB, parquet data)
- Energy modeling & prediction (Kepler, RAPL, PowerAPI, pod-level prediction models)
- Cooling systems & facility telemetry interpretation (BMS/DCIM data integration)
- Data wrangling and visualization (Pandas, PySpark, DVC, MLflow)
- Scientific reproducibility (experiment tracking, model versioning, FAIR datasets)
- HPC workload characterization (job patterns, resource usage clusters, performance variability)

## **Data Sources They Analyze**
- Monitoring data: node-level metrics (CPU/GPU utilization, power, temperature, fan speed)
- Logs: job scheduler logs, syslogs, application logs
- Batch scripts: SLURM/PBS job submission scripts (for workload classification & power estimation)
- Databases: Prometheus, PostgreSQL, InfluxDB, parquet archives
- Facility telemetry: PUE, cooling power, rack temperature distributions

## **Tools & Frameworks**
- HPC profiling tools (HPCToolkit, TAU, Score-P, VTune)
- Data analytics frameworks (Pandas, Dask, PySpark, SQL)
- Visualization (Grafana, Plotly, Matplotlib)
- ML/DL frameworks (Scikit-Learn, PyTorch, TensorFlow)
- Energy monitoring (Kepler, RAPL, IPMI)
- Cluster telemetry ingestion (Prometheus, ExaData, InfluxDB)
- Reproducibility stacks (MLflow, DVC, GitLab CI/CD)

## **Research Themes / Study Topics**
- System-wide anomaly detection (thermal, power, network)
- Predictive maintenance from multi-year logs
- Energy-aware job scheduling and node management
- Workload characterization and job class detection
- Cross-correlation of IT + facility data (server vs cooling)
- Data-driven optimization of cooling & compute efficiency
- Multi-modal telemetry fusion (metrics + logs + job scripts)


## **Example Queries for Multi-Agentic Chat System**

| # | Code | Category | Description | Example Queries | Priority |
|---|------|-----------|--------------|-----------------|-----------|
| 1 | **JOB** | **Job & Workflow Management** | Submitting, managing, and debugging jobs; handling queues and workflows. | “Submit my SLURM job script.”<br>“Show estimated queue wait time for GPU partition.”<br>“Cancel job 10234.”<br>“List my failed jobs this week.”<br>“Re-run job 4321 with longer walltime.” | **H** |
| 2 | **PERF** | **Performance & Optimization** | Profiling and optimizing application and system performance. | “Profile my job using nvprof.”<br>“Was my job memory-bound?”<br>“Identify MPI communication bottlenecks.”<br>“Compare runtime of exp_12 vs exp_15.”<br>“Suggest compiler flags for vectorization.” | **H** |
| 3 | **DATA** | **Data & Storage Management** | Managing data, I/O performance, and storage utilization. | “Copy results from scratch to project folder.”<br>“Check Lustre I/O bandwidth.”<br>“List large files in /scratch.”<br>“How much project storage is left?” | **M** |
| 4 | **MON** | **Monitoring & Observability** | Collecting and analyzing metrics, logs, and telemetry across nodes, jobs, and racks. | “Show CPU/GPU utilization for job 23456.”<br>“Plot my last week’s node usage.”<br>“Detect anomalies in node power consumption over the last 3 years.”<br>“Show temporal drift in node utilization distribution.” | **H** |
| 5 | **ENERGY** | **Power, Energy & Sustainability** | Monitoring energy usage, estimating job power cost, and analyzing sustainability KPIs. | “Estimate power cost of this batch script.”<br>“Which jobs caused thermal stress in 2023.”<br>“Correlate cooling energy and compute load during summer 2024.”<br>“Generate energy efficiency report for my project.”<br>“Show thermal map of GPU nodes.” | **H** |
| 6 | **FAC** | **Facility, Infrastructure & Environmental Systems** | Managing racks, CRAC units, alarms, and environmental sensors (temperature, humidity, PUE). | “Which racks show thermal anomalies?”<br>“Alarm history for CRAC unit 3.”<br>“Show cooling efficiency by zone.”<br>“Current PUE trend for datacenter.” | **L** |
| 7 | **SEC** | **Security, Access & Policy Management** | Handling IAM, quota limits, authentication, and compliance queries. | “Why was my SSH access denied?”<br>“Show my remaining quota.”<br>“Which users can access dataset X?” | **L** |
| 8 | **ARCH** | **System Architecture, Design & Capacity Planning** | Understanding and planning HPC system design, capacity, and scalability. | “Which nodes have A100 GPUs?”<br>“Show topology of interconnect fabric.”<br>“Forecast storage capacity for next year.”<br>“Compare rack power density trends.” | **M** |
| 9 | **AIOPS** | **AI, Automation & Intelligent Operations** | ML/AI-driven analytics for anomaly detection, predictive maintenance, and optimization. | “Detect cooling anomalies using ML models.”<br>“Predict node failure probability.”<br>“Generate feature dataset for model training from Prometheus + SLURM logs.”<br>“Recommend energy-aware job scheduling.” | **H** |
| 10 | **DOCS** | **Documentation, Support & Knowledge Assistance** | Providing knowledge, tutorials, troubleshooting, and HPC best practices. | “How to run TensorFlow with SLURM?”<br>“Explain difference between partitions.”<br>“Show documentation for Kepler energy plugin.” | **M** |

## Priority Tags Summary

| Priority | Meaning | Categories |
|----------|---------|------------|
| **H (High)** | Frequent, critical for research workflows | Job Submission, Resource Discovery, Monitoring, Debugging, Profiling, Data Management |
| **M (Medium)** | Periodic needs | Environment Setup, Reproducibility, Documentation, Visualization |
| **L (Low)** | Rare but high-value | Facility Awareness, Security, Collaboration |

---

