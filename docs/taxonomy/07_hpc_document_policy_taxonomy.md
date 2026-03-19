
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

## 📋 Detailed Document Taxonomy Table

The table below enumerates each document type with structured identifiers and mappings used for RAG ingestion and query routing:

- **doc_key** — Machine-readable identifier for each document type.
- **primary_qcat / secondary_qcat** — Global HPC Query Categories (see [02_query_categories.md](02_query_categories.md)); used for retrieval and question classification.
- **intended_users** — Target audience for the document type.

| doc_key               | doc_name                               | group_id | group_name                                            | description                                                                | common_formats          | owners                         | primary_qcat | secondary_qcat | intended_users                   |
| --------------------- | -------------------------------------- | -------- | ----------------------------------------------------- | -------------------------------------------------------------------------- | ----------------------- | ------------------------------ | ------------ | -------------- | -------------------------------- |
| ARCH_OVERVIEW         | System Overview Document               | 1        | System Architecture & Hardware Documentation          | Cluster architecture diagrams, vendor topology, compute node distribution. | PDF, Markdown, PNG, SVG | System Architects, Vendors     | ARCH         | DOCS           | Architects;Sysadmins;Management  |
| ARCH_HW_DATASHEETS    | Hardware Data Sheets                   | 1        | System Architecture & Hardware Documentation          | CPU/GPU specs, RAM configuration, NIC types, storage controllers.          | PDF, XLSX               | System Architects, Procurement | ARCH         | FAC            | Architects;Sysadmins             |
| ARCH_RACK_LAYOUT      | Rack Layout Diagrams                   | 1        | System Architecture & Hardware Documentation          | Physical rack layout, node numbering, cooling zones.                       | Visio, PNG, PDF         | Facility Engineers, Architects | FAC          | ARCH           | Facility;Sysadmins;Architects    |
| ARCH_NETWORK_TOPOLOGY | Network Topology Docs                  | 1        | System Architecture & Hardware Documentation          | Infiniband/Ethernet hierarchy, VLAN map, routing configuration.            | PDF, Markdown, SVG      | Network Engineers              | ARCH         | SEC            | Network;Sysadmins;Architects     |
| ARCH_STORAGE_DESIGN   | Storage Architecture Docs              | 1        | System Architecture & Hardware Documentation          | Lustre/Ceph/BeeGFS layout, MDT/OST map, performance tiers.                 | PDF, Markdown           | Storage Architects             | ARCH         | DATA           | Storage;Sysadmins;Architects     |
| ARCH_BOM              | Bill of Materials (BoM)                | 1        | System Architecture & Hardware Documentation          | Component inventory, serial numbers, firmware levels.                      | XLSX, CSV, PDF          | Procurement, Asset Management  | ARCH         | DOCS           | Procurement;Sysadmins;Management |
| ARCH_BIOS_CFG         | Firmware & BIOS Configuration          | 1        | System Architecture & Hardware Documentation          | BIOS templates, SMT/NUMA, turbo mode settings.                             | TXT, PDF, Markdown      | Sysadmins, Vendors             | ARCH         | SEC            | Sysadmins                        |
| OPS_ACCOUNT_POLICY    | User Account Management Policy         | 2        | System Administration & Operations Manuals            | Creation/deletion workflow, LDAP groups, SSH key management.               | PDF, Wiki               | Sysadmins, IAM                 | SEC          | DOCS           | Sysadmins;Helpdesk               |
| OPS_SCHEDULER_CONFIG  | Queue / Scheduler Config Docs          | 2        | System Administration & Operations Manuals            | SLURM partitions, fairshare policy, accounting settings.                   | CONF, Markdown          | Sysadmins                      | JOB          | SEC            | Sysadmins                        |
| OPS_BACKUP_RESTORE    | Backup & Restore Procedures            | 2        | System Administration & Operations Manuals            | Backup frequency, retention, restore guide.                                | PDF, Markdown           | Sysadmins, Data Managers       | DATA         | SEC            | Sysadmins;Data Managers          |
| OPS_DR_PLAN           | Disaster Recovery Plan                 | 2        | System Administration & Operations Manuals            | Failover strategy, contacts, offsite recovery.                             | PDF                     | Sysadmins, Management          | SEC          | FAC            | Sysadmins;Management             |
| OPS_SW_INSTALL_POLICY | Software Installation & Module Policy  | 2        | System Administration & Operations Manuals            | Module structure, compiler guidelines, testing workflow.                   | Markdown                | Sysadmins                      | DOCS         | JOB            | Sysadmins;Users                  |
| OPS_MAINTENANCE_PROC  | Maintenance Procedures                 | 2        | System Administration & Operations Manuals            | Firmware upgrade checklists, preventive maintenance tasks.                 | PDF, Wiki               | Sysadmins                      | FAC          | ARCH           | Sysadmins                        |
| OPS_CHANGE_MGMT       | Change Management Process              | 2        | System Administration & Operations Manuals            | Request, approval, rollback documentation.                                 | PDF                     | Sysadmins, Management          | SEC          | DOCS           | Sysadmins;Management             |
| OPS_RBAC              | Access Control Policy (RBAC)           | 2        | System Administration & Operations Manuals            | Roles, sudoers configuration, escalation rules.                            | PDF, YAML               | Sysadmins, Security            | SEC          | DOCS           | Sysadmins;Security               |
| FAC_LAYOUT            | Facility Layout Plan                   | 3        | Facility & Infrastructure Documentation               | Floor maps, airflow, rack placement.                                       | CAD, PDF, PNG           | Facility Engineers             | FAC          | ARCH           | Facility;Architects              |
| FAC_COOLING_DESIGN    | Cooling System Design                  | 3        | Facility & Infrastructure Documentation               | CRAC/CRAH, RDHX, chilled water system, P&ID diagrams.                      | PDF, PNG                | Facility Engineers             | FAC          | ENERGY         | Facility                         |
| FAC_POWER_DIST        | Power Distribution Docs                | 3        | Facility & Infrastructure Documentation               | UPS/PDU specs, breaker list, one-line diagram.                            | PDF, DWG                | Facility Engineers, Electrical | FAC          | ENERGY         | Facility                         |
| FAC_SETPOINTS         | Setpoint & Control Standards           | 3        | Facility & Infrastructure Documentation               | Temperature, humidity, pressure, flow thresholds.                           | PDF, CSV                | Facility Engineers             | FAC          | ENERGY         | Facility;Sysadmins               |
| FAC_BMS_DCIM          | BMS/DCIM Configuration Docs            | 3        | Facility & Infrastructure Documentation               | Tag lists, SNMP/Modbus registers, alarm codes.                             | CSV, PDF                | Facility Engineers             | FAC          | SEC            | Facility;Sysadmins               |
| FAC_MAINT_LOGS        | Facility Maintenance Logs (Structured) | 3        | Facility & Infrastructure Documentation               | HVAC, pump, chiller inspection records.                                    | CSV, XLSX               | Facility Engineers             | FAC          | DOCS           | Facility                         |
| FAC_STANDARDS         | Facility Standards & Certifications    | 3        | Facility & Infrastructure Documentation               | ASHRAE TC9.9, ISO 50001, EN 50600.                                         | PDF                     | Facility Engineers, Compliance | FAC          | SEC            | Facility;Management              |
| USER_ONBOARD          | User Onboarding Guide                  | 4        | User Documentation & Help Resources                   | Registration, VPN, authentication, terms of use.                           | PDF, Wiki               | User Support                   | DOCS         | SEC            | Users;Helpdesk                   |
| USER_QUICKSTART       | Quick Start Guide                      | 4        | User Documentation & Help Resources                   | Login, job submission, file transfer basics.                               | PDF                     | User Support                   | DOCS         | JOB            | Users                            |
| USER_SCHED_GUIDES     | SLURM/PBS/LSF Guides                   | 4        | User Documentation & Help Resources                   | Job scheduling commands, partitions, limits.                               | PDF, Markdown           | User Support, Sysadmins        | JOB          | DOCS           | Users;Sysadmins                  |
| USER_SBATCH_TEMPLATES | Batch Script Examples                  | 4        | User Documentation & Help Resources                   | CPU/GPU templates, MPI, containers.                                        | TXT, .sbatch            | User Support                   | JOB          | PERF           | Users                            |
| USER_MODULES          | Software Module Reference              | 4        | User Documentation & Help Resources                   | Installed software, versions, usage examples.                              | HTML, Markdown          | Sysadmins                      | DOCS         | JOB            | Users;Sysadmins                  |
| USER_STORAGE_POLICY   | Data Storage & Quota Policy            | 4        | User Documentation & Help Resources                   | Home/project/scratch rules, retention.                                     | PDF                     | Data Managers                  | DATA         | DOCS           | Users;Data Managers              |
| USER_ACCOUNTING       | Accounting & Usage Policy              | 4        | User Documentation & Help Resources                   | CPU/GPU hour limits, billing, allocations.                                 | PDF                     | Management, Admin              | DATA         | DOCS           | Users;Admins                     |
| USER_HELPDESK_FAQ     | Helpdesk & FAQ                         | 4        | User Documentation & Help Resources                   | Ticket submission, support levels, escalation.                             | Wiki, HTML              | Helpdesk                       | DOCS         | JOB            | Users;Helpdesk                   |
| USER_TRAINING         | Training Materials                     | 4        | User Documentation & Help Resources                   | Workshop slides, tutorials, example datasets.                              | PDF, PPTX               | User Support                   | DOCS         | PERF           | Users                            |
| DATA_CLASSIFICATION   | Data Classification Policy             | 5        | Data Management & Governance                          | Confidentiality levels and labeling.                                       | PDF                     | Data Managers, Security        | SEC          | DATA           | Users;Data Managers              |
| DATA_BACKUP_ARCHIVE   | Backup & Archival Policy               | 5        | Data Management & Governance                          | Retention time, offsite copies, recovery verification.                     | PDF                     | Data Managers                  | DATA         | SEC            | Data Managers;Sysadmins          |
| DATA_RETENTION        | Data Retention Policy                  | 5        | Data Management & Governance                          | Automatic purging, project expiration.                                     | PDF                     | Data Managers                  | DATA         | SEC            | Data Managers;Users              |
| DATA_TRANSFER         | Data Transfer Policy                   | 5        | Data Management & Governance                          | Approved tools (scp, rsync, Globus), bandwidth quotas.                     | PDF                     | Data Managers, Security        | DATA         | SEC            | Users;Sysadmins                  |
| DATA_GDPR             | GDPR / Compliance Docs                 | 5        | Data Management & Governance                          | Privacy and EU data-handling standards.                                    | PDF                     | Legal, Data Protection Officer | SEC          | DOCS           | All                              |
| DATA_RDM              | Research Data Management Plan (RDM)    | 5        | Data Management & Governance                          | Templates for user projects.                                                | PDF, DOCX               | Data Managers                  | DATA         | DOCS           | Users;PIs                        |
| POL_AUP               | Acceptable Use Policy (AUP)            | 6        | Organizational & Policy Documents                     | Authorized activities and prohibited actions.                              | PDF                     | Management, Legal              | SEC          | DOCS           | All Users                        |
| POL_SLA               | Service Level Agreement (SLA)          | 6        | Organizational & Policy Documents                     | Uptime targets, response SLAs, maintenance windows.                        | PDF                     | Management                     | DOCS         | SEC            | Users;Management                 |
| POL_SECURITY          | Security Policy                        | 6        | Organizational & Policy Documents                     | Passwords, MFA, access control, vulnerabilities.                           | PDF                     | Security, Sysadmins            | SEC          | DOCS           | All                              |
| POL_INCIDENT          | Incident Response Plan                 | 6        | Organizational & Policy Documents                     | Escalation tree, templates, response timeline.                            | PDF                     | Security, Management           | SEC          | DOCS           | Sysadmins;Security;Management   |
| POL_CHANGE_CONTROL    | Change Control Policy                  | 6        | Organizational & Policy Documents                     | Approval and audit trails for changes.                                     | PDF                     | Management, Sysadmins          | SEC          | DOCS           | Sysadmins;Management             |
| POL_ENERGY            | Energy Management Policy               | 6        | Organizational & Policy Documents                     | PUE targets, sustainability goals, renewable integration.                  | PDF                     | Sustainability, Facility       | ENERGY       | FAC            | Management;Facility             |
| POL_PROCUREMENT       | Procurement Policy                     | 6        | Organizational & Policy Documents                     | Vendor selection, tendering process, contracts.                             | PDF                     | Procurement, Management        | DOCS         | SEC            | Management;Procurement           |
| POL_HS                | Health & Safety Policy                 | 6        | Organizational & Policy Documents                     | On-site conduct, hazard identification, PPE.                              | PDF                     | Facility, HSE                  | FAC          | SEC            | All On-site                      |
| POL_ENV_REPORTS       | Environmental & Sustainability Reports | 6        | Organizational & Policy Documents                     | Energy consumption, carbon footprint summaries.                             | PDF, XLSX               | Sustainability, Management     | ENERGY       | DOCS           | Management                       |
| ADMIN_USER_DB         | User Database (Structured)             | 7        | Administrative & Organizational Data                  | Usernames, roles, projects, affiliations.                                  | CSV, LDAP               | Admins, IAM                    | DOCS         | SEC            | Admins;Sysadmins                 |
| ADMIN_ALLOCATIONS     | Project Allocation Docs                | 7        | Administrative & Organizational Data                  | Quotas, dates, utilization history.                                        | PDF, XLSX               | Admins, Management             | DATA         | DOCS           | Admins;Management                |
| ADMIN_BILLING         | Accounting / Billing Rules             | 7        | Administrative & Organizational Data                  | Cost-per-node-hour, GPU pricing, summaries.                                | XLSX, Markdown          | Admins, Finance                | DATA         | DOCS           | Admins;Finance                   |
| ADMIN_MAINT_CAL       | Maintenance Calendar                   | 7        | Administrative & Organizational Data                  | Scheduled downtime, upgrade notifications.                                | ICS, Wiki               | Sysadmins                      | DOCS         | FAC            | Sysadmins;Users                  |
| ADMIN_CONTRACTS       | Vendor Contracts / Warranties          | 7        | Administrative & Organizational Data                  | Service agreements, expiration dates.                                      | PDF                     | Procurement, Legal             | DOCS         | SEC            | Procurement;Management          |
| ADMIN_INVOICES        | Procurement Invoices & Specs           | 7        | Administrative & Organizational Data                  | Purchase orders, component quotes.                                         | PDF, XLSX               | Procurement                    | DOCS         | DATA           | Procurement;Finance              |
| KB_INTERNAL_PAGES     | Internal Wiki Pages                    | 8        | Knowledge Base / Wiki / Portal Content                | Centralized documentation on system, users, software, policy.              | Markdown, HTML          | All Teams                      | DOCS         | ARCH           | All                              |
| KB_FAQ                | FAQ / Troubleshooting Pages            | 8        | Knowledge Base / Wiki / Portal Content                | Job errors, permissions, data transfer issues.                             | Markdown, HTML          | Helpdesk                       | DOCS         | JOB            | Users;Helpdesk                   |
| KB_BEST_PRACTICES     | Best Practice Guides                   | 8        | Knowledge Base / Wiki / Portal Content                | Performance, energy, storage optimization.                                 | Markdown                | User Support, Admins           | DOCS         | PERF           | Users;Admins                     |
| KB_ARCH_OVERVIEWS     | Architecture Overview Pages            | 8        | Knowledge Base / Wiki / Portal Content                | Node types, interconnect overview, software stack.                         | HTML, SVG               | Architects                     | DOCS         | ARCH           | Users;Architects                 |
| KB_HOWTOS             | Procedural How-Tos                     | 8        | Knowledge Base / Wiki / Portal Content                | Add users, update modules, restart services.                                | Wiki                    | Helpdesk, Sysadmins            | DOCS         | SEC            | Sysadmins;Helpdesk               |
| KB_PUBLIC_SITE        | Public Website Content                 | 8        | Knowledge Base / Wiki / Portal Content                | News, events, announcements, status pages.                                 | HTML                    | Comms, User Support            | DOCS         | JOB            | Users;Public                     |
| KB_KB_DB              | Helpdesk Portal Knowledge Base         | 8        | Knowledge Base / Wiki / Portal Content                | Searchable solutions and resolutions.                                      | DB export, JSON         | Helpdesk                       | DOCS         | JOB            | Helpdesk;Users                   |
| REF_THERMAL           | Thermal & Environmental Setpoints      | 9        | Reference Standards, Setpoints & Configuration Tables | Inlet/outlet temperature, humidity, airflow.                               | CSV, PDF                | Facility, Sysadmins            | FAC          | ENERGY         | Facility;Sysadmins               |
| REF_POWER             | Power & Electrical Standards           | 9        | Reference Standards, Setpoints & Configuration Tables | Rack power limits, breaker capacities.                                     | PDF                     | Facility                       | FAC          | ENERGY         | Facility                         |
| REF_SW_STANDARDS      | Software Configuration Standards       | 9        | Reference Standards, Setpoints & Configuration Tables | Compiler flags, MPI versions, CUDA guidelines.                             | Markdown, YAML          | Sysadmins                      | ARCH         | PERF           | Sysadmins;Users                  |
| REF_FAC_COMPLIANCE    | Facility Compliance Standards          | 9        | Reference Standards, Setpoints & Configuration Tables | ASHRAE, ISO, EN documentation.                                             | PDF                     | Facility, Compliance           | FAC          | SEC            | Facility;Management              |
| REF_NODE_GROUPS       | Node Group Definitions                 | 9        | Reference Standards, Setpoints & Configuration Tables | Production/test/dev node groups.                                           | YAML, CONF              | Sysadmins                      | JOB          | ARCH           | Sysadmins                        |
| REF_QUEUE_DEFS        | Queue Definitions                      | 9        | Reference Standards, Setpoints & Configuration Tables | Partition list, limits, timeouts.                                          | CONF, Markdown          | Sysadmins                      | JOB          | SEC            | Sysadmins;Users                  |
| ENG_TENDER            | Tender / Procurement Docs              | 10       | Design, Engineering & Upgrade Documents               | RFPs, vendor proposals, bid evaluations.                                   | PDF                     | Procurement, Architects        | ARCH         | DOCS           | Management;Procurement           |
| ENG_SAT               | System Acceptance Tests (SAT)          | 10       | Design, Engineering & Upgrade Documents               | Benchmark results, validation reports.                                     | PDF                     | Architects, Sysadmins          | ARCH         | PERF           | Architects;Sysadmins             |
| ENG_UPGRADES          | Upgrade / Expansion Plans              | 10       | Design, Engineering & Upgrade Documents               | Additional racks, new cooling capacity, GPU extensions.                    | PDF                     | Architects, Facility           | ARCH         | FAC            | Architects;Facility;Management  |
| ENG_INTEGRATION       | Integration Diagrams                   | 10       | Design, Engineering & Upgrade Documents               | Facility-to-system interconnects, network links.                           | Visio, SVG              | Architects                     | ARCH         | FAC            | Architects;Facility             |
| ENG_CHANGE_FORMS      | Change Request Forms                   | 10       | Design, Engineering & Upgrade Documents               | RFC templates, justification documents.                                    | DOCX                    | Sysadmins, Management          | SEC          | DOCS           | Sysadmins;Management             |

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

