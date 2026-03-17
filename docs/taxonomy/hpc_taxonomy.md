
# 🧱 HPC Datacenter Knowledge Base — Document & Policy Taxonomy (RAG-Ingestible Sources)

> **Scope:**  
> This taxonomy lists all *static and semi-static knowledge* sources in an HPC datacenter.  
> It **excludes monitoring, telemetry, logs, and time-series data**, and instead focuses on  
> **documents, wikis, PDFs, manuals, and policy artifacts** suitable for ingestion into an HPC RAG system.

---

## 🗂️ 1. System Architecture & Hardware Documentation

### Overview
High-level and component-level documentation describing the compute, storage, and network design of the HPC system.

### Examples
- **System Overview Document:** Cluster architecture diagrams, vendor topology, compute node distribution.
- **Hardware Data Sheets:** CPU/GPU specs, RAM configuration, NIC types, storage controllers.
- **Rack Layout Diagrams:** Physical rack layout, node numbering, cooling zones.
- **Network Topology Docs:** Infiniband/Ethernet hierarchy, VLAN map, routing configuration.
- **Storage Architecture Docs:** Lustre, Ceph, BeeGFS layout and performance tiers.
- **Bill of Materials (BoM):** Component inventory, serial numbers, firmware levels.
- **Firmware & BIOS Configuration:** BIOS templates, SMT, NUMA, turbo mode settings.

### Formats
`PDF`, `Markdown`, `Visio`, `PNG`, `SVG`, `XLSX`

---

## 🧩 2. System Administration & Operations Manuals

### Overview
Internal documentation defining how administrators manage users, queues, software, and system configuration.

### Examples
- **User Account Management Policy:** Creation/deletion workflow, LDAP group mapping, SSH access.
- **Queue / Scheduler Config Docs:** SLURM partitions, fairshare policy, accounting settings.
- **Backup & Restore Procedures:** Backup frequency, retention, restore guide.
- **Disaster Recovery Plan:** Failover strategy, contact list, offsite recovery details.
- **Software Installation Policy:** Module tree structure, compiler guidelines, testing workflow.
- **Maintenance Procedures:** Firmware upgrade checklists, preventive maintenance tasks.
- **Change Management Process:** Request, approval, and rollback documentation.
- **Access Control Policy (RBAC):** Roles, sudoers configuration, escalation rules.

### Formats
`PDF`, `Markdown`, `YAML`, `CONF`

---

## 🏢 3. Facility & Infrastructure Documentation

### Overview
Documents describing the physical environment, cooling systems, power distribution, and environmental standards.

### Examples
- **Facility Layout Plan:** Floor maps, airflow and rack placement.
- **Cooling System Design:** CRAC/CRAH, RDHX, chilled water system, P&ID diagrams.
- **Power Distribution Docs:** UPS and PDU specifications, breaker list, one-line diagram.
- **Setpoint & Control Standards:** Temperature, humidity, pressure, and flow thresholds.
- **BMS/DCIM Configuration Docs:** Tag list, SNMP/Modbus registers, alarm codes.
- **Maintenance Logs:** Pump, chiller, HVAC maintenance records.
- **Facility Standards:** ASHRAE TC9.9, ISO 50001, EN 50600 compliance documentation.

### Formats
`PDF`, `DWG`, `CSV`, `XLSX`, `CAD`, `PNG`

---

## ⚙️ 4. User Documentation & Help Resources

### Overview
Guides and references for end users, researchers, and application scientists on how to use the HPC system effectively.

### Examples
- **User Onboarding Guide:** Account creation, VPN, authentication, terms of use.
- **Quick Start Guide:** Login, job submission, file transfer basics.
- **SLURM / PBS / LSF Guides:** Job scheduling commands, partitions, queue limits.
- **Batch Script Examples:** CPU/GPU templates, MPI, hybrid jobs, Singularity/Podman containers.
- **Software Module Reference:** Installed software, versions, usage examples.
- **Data Storage & Quota Policy:** Home, project, scratch filesystem details and retention rules.
- **Accounting & Usage Policy:** CPU/GPU hour limits, billing formula, allocation policies.
- **Helpdesk & FAQ:** Ticket submission, support levels, escalation procedures.
- **Training Materials:** Workshop slides, video tutorials, example datasets.

### Formats
`PDF`, `Markdown`, `HTML`, `TXT`, `.sbatch`, `PPTX`

---

## 💾 5. Data Management & Governance

### Overview
Policies and standards governing how user and system data are stored, transferred, and retained.

### Examples
- **Data Classification Policy:** Confidentiality levels and labeling.
- **Backup & Archival Policy:** Retention time, offsite copies, recovery verification.
- **Data Retention Policy:** Automatic purging, project expiration.
- **Data Transfer Policy:** Approved tools (scp, rsync, Globus), bandwidth quotas.
- **GDPR / Compliance Docs:** Privacy protection and EU data-handling standards.
- **Research Data Management Plan (RDM):** Templates for user projects.

### Formats
`PDF`, `DOCX`, `Markdown`

---

## 🧭 6. Organizational & Policy Documents

### Overview
Institutional rules, operational policies, and service-level agreements governing HPC use and operation.

### Examples
- **Acceptable Use Policy (AUP):** Authorized activities and prohibited actions.
- **Service Level Agreement (SLA):** Uptime targets, response SLAs, maintenance window.
- **Security Policy:** Passwords, MFA, access control, vulnerability management.
- **Incident Response Plan:** Escalation tree, reporting templates, response timeline.
- **Change Control Policy:** Approval and audit trails for configuration changes.
- **Energy Management Policy:** PUE targets, sustainability goals, renewable integration.
- **Procurement Policy:** Vendor selection, tendering process, contract lifecycle.
- **Health & Safety Policy:** On-site conduct, hazard identification, PPE requirements.
- **Environmental & Sustainability Reports:** Energy consumption, carbon footprint summaries.

### Formats
`PDF`, `Markdown`, `DOCX`

---

## 🧮 7. Administrative & Organizational Data

### Overview
Structured documents supporting project management, accounting, and asset control.

### Examples
- **User Database (Structured):** Usernames, roles, projects, affiliations.
- **Project Allocation Docs:** Resource quotas, start/end dates, utilization history.
- **Accounting / Billing Rules:** Cost-per-node-hour, GPU pricing, monthly summaries.
- **Maintenance Calendar:** Scheduled downtime, upgrade notifications.
- **Vendor Contracts / Warranties:** Service agreements, expiration dates.
- **Procurement Invoices & Specs:** Purchase orders, component quotes.

### Formats
`CSV`, `XLSX`, `PDF`, `Markdown`

---

## 🧱 8. Knowledge Base / Wiki / Portal Content

### Overview
Human-readable pages used in helpdesks, wikis, or internal documentation systems.

### Examples
- **Internal Wiki Pages:** Confluence, GitLab, or MediaWiki-based documentation.
- **FAQ / Troubleshooting Pages:** Job errors, permission issues, data transfer errors.
- **Best Practice Guides:** Performance optimization, energy efficiency, storage optimization.
- **Architecture Overview Pages:** Node types, interconnect overview, software stack.
- **Procedural How-Tos:** Steps to add users, update modules, restart services.
- **Public Website Content:** News, events, announcements, status pages.
- **Helpdesk Portal Knowledge Base:** Solutions and resolutions searchable database.

### Formats
`Markdown`, `HTML`, `Wiki export`, `JSON`

---

## 🏷️ 9. Reference Standards, Setpoints & Configuration Tables

### Overview
Reference parameters, configuration files, and technical standards used for consistency and compliance.

### Examples
- **Thermal & Environmental Setpoints:** Inlet/outlet temperature, humidity, airflow.
- **Power & Electrical Standards:** Rack power limits, breaker capacities.
- **Software Configuration Standards:** Compiler flags, MPI versions, CUDA guidelines.
- **Facility Compliance Standards:** ASHRAE, ISO, EN documentation.
- **Node Group Definitions:** Production/test/dev node groups.
- **Queue Definitions:** Partition list, limits, timeouts.

### Formats
`CSV`, `YAML`, `CONF`, `PDF`

---

## 🧰 10. Design, Engineering & Upgrade Documents

### Overview
Documents produced during system acquisition, expansion, and commissioning.

### Examples
- **Tender / Procurement Docs:** RFPs, vendor proposals, bid evaluations.
- **System Acceptance Tests (SAT):** Benchmark results, validation reports.
- **Upgrade / Expansion Plans:** Additional racks, new cooling capacity, GPU extensions.
- **Integration Diagrams:** Facility-to-system interconnects, network links.
- **Change Request Forms:** RFC templates, justification documents.

### Formats
`PDF`, `DOCX`, `XLSX`, `Visio`, `SVG`

---

## ✅ Summary Table

| # | Group | Description | Common Formats | Owners / Stakeholders |
|---|--------|--------------|----------------|-----------------------|
| 1 | **System Architecture Docs** | Compute, storage, and network design | PDF, Markdown | Architects |
| 2 | **System Admin & Ops Docs** | Configuration, account, queue management | Markdown, YAML | Sysadmins |
| 3 | **Facility & Infrastructure Docs** | Cooling, power, layout, standards | PDF, CAD | Facility engineers |
| 4 | **User Documentation** | Onboarding, job scripts, guides | PDF, Wiki | User support |
| 5 | **Data Governance** | Backup, transfer, retention, GDPR | PDF | Data managers |
| 6 | **Organizational Policies** | AUP, SLA, security, sustainability | PDF | Management |
| 7 | **Administrative Data** | Accounting, projects, vendors | XLSX, CSV | Admins |
| 8 | **Knowledge Base / Wiki** | How-to guides, FAQs, KB articles | Markdown, HTML | All teams |
| 9 | **Reference Standards** | Setpoints, configs, compliance | CSV, CONF | Facility + Sysadmin |
| 10 | **Engineering Docs** | Design, procurement, upgrades | PDF, DOCX | Architects |

---

## 📂 Suggested Folder Structure for RAG Ingestion

```

rag_corpus/
├── 01_system_architecture/
├── 02_admin_operations/
├── 03_facility_infrastructure/
├── 04_user_docs/
├── 05_data_governance/
├── 06_policies/
├── 07_admin_data/
├── 08_wiki_kb/
├── 09_standards/
└── 10_engineering_design/

```

Each folder can store:
- **Original PDFs / Docs**
- **Extracted text (Markdown/JSON)**
- **Metadata.yaml** → contains `title`, `source`, `tags`, `owner`, `date_updated`, etc.

---

## 🧩 Example Metadata Schema (YAML)

```yaml
title: "HPC User Onboarding Guide"
category: "04_user_docs"
owner: "HPC User Support Team"
source_format: "PDF"
last_updated: "2025-03-01"
tags: ["onboarding", "registration", "vpn", "ssh", "policy"]
confidentiality: "public"
summary: "Explains how new users register, authenticate, and access HPC resources."
````

---

**✅ Purpose:**
This Markdown file defines *all categories of textual and policy-based documentation* in an HPC datacenter that can be ingested into a **Retrieval-Augmented Generation (RAG)** system — supporting question answering, policy search, and contextual retrieval without accessing live telemetry or monitoring data.

---

