# 🧩 Permissions & Access Control Policy (Improved)

This section defines the **role-based access control (RBAC)** and data exposure policies for all HPC user interactions within the ExaBench-QA / ODA Agent framework.  
It ensures **data privacy**, **system security**, and **tiered visibility** according to user responsibilities.

---

## 🔐 Access Control Overview

| **Access Level** | **Intended Users** | **Scope of Access** | **Examples / Notes** |
|------------------|-------------------|---------------------|----------------------|
| **User-Level (Public)** | Normal HPC Users, Researchers | Safe, authenticated user operations | Job submission, monitoring, quota check, performance profiling, documentation queries |
| **Elevated / Privileged** | System Admins, Project Managers | Requires explicit privilege or approval | Software installation, system configuration, user management |
| **Restricted / Read-Only** | Researchers, Designers | Limited aggregated view of sensitive data | Power trends, energy metrics, facility telemetry (anonymized or aggregated) |
| **Sensitive / Admin-Only** | Sysadmins, Security Officers | Critical infrastructure, security, or access control data | Authentication logs, security configurations, network details |
| **Highly Sensitive (Isolated Mode)** | Senior Architects, Facility Operators | Confidential or policy-bound data | Procurement details, physical access design, cybersecurity models |

---

## 🧠 Functional Permissions Matrix

| **Category** | **Access Level** | **Data Visibility** | **Notes** |
|---------------|------------------|----------------------|------------|
| **Job Submission, Monitoring & Profiling** | User-Level | Own jobs only | Accessible via authenticated HPC accounts and RAG-safe queries |
| **Resource Discovery & Topology Visualization** | User-Level | Aggregated system data | No node-level or IP-sensitive exposure |
| **Data Management (Home/Project Directories)** | User-Level | Owned or group directories | Enforced by filesystem ACLs and quotas |
| **Debugging & Logs** | User-Level | Own job logs | No cross-user log access |
| **Software Installation & Environment Modules** | Elevated | Cluster-wide with approval | Admin validation required for new system packages |
| **Storage & GPU Requests** | User-Level (quota-limited) | Resource quota enforcement | Bound by project-level resource allocations |
| **Collaboration & Security Management** | Privileged | Project-level scope | Requires sysadmin or manager intervention |
| **Facility / Power / Energy Awareness** | Restricted Read-Only | Aggregated, anonymized | For sustainability research and modeling only |
| **System Configuration, Network, Security Policies** | Sensitive | Hidden from general users | Exposed only through secured admin APIs |

---

## 🧱 Access Tier Definitions

| **Tier** | **Access Description** | **Applies To** | **Security Controls** |
|-----------|------------------------|----------------|------------------------|
| 🟢 **Tier-1: Public/User-Level** | Safe-to-share documentation and non-sensitive RAG data | Manuals, simulations, general system info | No approval needed |
| 🟡 **Tier-2: Privileged (Admin/Architect)** | Requires elevated credentials | Real telemetry (power, temperature, network) | Role-based token validation |
| 🔵 **Tier-3: Restricted Read-Only** | Observational, no modification | Energy dashboards, facility KPIs | Enforced read-only mode |
| 🔴 **Tier-4: Highly Sensitive** | Confidential system data | Procurement, cybersecurity, access control | Approval + isolation environment |

---

## 🧾 Policy Notes

- **Least-Privilege Principle:** Each role receives only the minimum access required to perform its tasks.  
- **Secure Routing:** Sensitive requests must pass through the **Admin-Only Secure Agent** for audit and control.  
- **Data Anonymization:** Facility and energy telemetry shared with researchers must be **aggregated and anonymized**.  
- **Audit Logging:** All elevated or privileged actions are **logged and reviewable** by compliance officers.  
- **Default Read-Only Mode:** Unless explicitly required, access to monitoring and telemetry is **non-modifiable**.

---

✅ **Summary**

| **User Type** | **Typical Access Level** | **Main Data Domain** |
|----------------|---------------------------|----------------------|
| Normal HPC User | User-Level | Jobs, storage, monitoring |
| HPC Researcher | Restricted Read-Only | Aggregated telemetry, power data |
| System Administrator | Elevated / Sensitive | Full cluster, logs, configurations |
| Facility Engineer | Privileged / Restricted | Power, cooling, infrastructure |
| HPC Architect / Designer | Privileged | System models, design simulations |

---
