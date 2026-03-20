# ExaBench HPC Facility — RBAC and Access Policy

**Policy version:** 1.0
**Effective date:** 2026-03-19
**Document ID:** rbac_policy_env_10

---

## 1. Role Definitions

This facility recognises five user roles. Roles are mutually exclusive per user session.

| Role | Description | Typical user |
|------|-------------|--------------|
| `scientific_user` | Standard HPC user; accesses own jobs only | Graduate student, postdoc |
| `researcher` | Elevated user; accesses project-level data | Senior researcher, PI |
| `sysadmin` | System administrator; full operational access | HPC operations staff |
| `facility_admin` | Facility administrator; policy and budget authority | Facility director, manager |
| `system_designer` | Read-only systems analysis; full data visibility for design tasks | Architect, capacity planner |

---

## 2. Partition Access Rules

| Partition | Allowed roles | Max walltime | Notes |
|-----------|--------------|--------------|-------|
| `cpu`     | all roles | 48h (`scientific_user`, `researcher`), 168h (`sysadmin`, `facility_admin`) | General-purpose compute |
| `gpu`     | `researcher`, `sysadmin`, `facility_admin` | 72h | Requires GPU allocation |
| `highmem` | `sysadmin`, `facility_admin` | 168h | >512 GB RAM nodes |
| `debug`   | all roles | 1h, ≤2 nodes | Interactive testing only |
| `restricted` | `sysadmin`, `facility_admin` (plus approved accounts) | 168h | Requires PI approval |

To submit to a partition your role does not have access to by default, submit an access request (see §5).

---

## 3. Data Access Tiers

| Tier | Label | Data types | Access |
|------|-------|-----------|--------|
| tier1_public | Public | Partition status, own job state, docs | All roles, no approval |
| tier2_privileged | Privileged | Full node telemetry, other users' job details, incident logs | `sysadmin`, `facility_admin`; formal request + facility_admin approval for others |
| tier3_restricted | Restricted | Energy dashboards, power KPIs, billing, cluster PUE | `facility_admin`, `system_designer` |
| tier4_sensitive | Sensitive | Security audit logs, procurement records, personnel data | Explicit grant from facility director |

---

## 4. Allowed Tools by Role

Tools not listed for a role are **forbidden** — the agent must not invoke them.

| Tool | `scientific_user` | `researcher` | `sysadmin` | `facility_admin` | `system_designer` |
|------|-------------------|--------------|-----------|-----------------|------------------|
| `slurm` (own jobs only) | ✓ | ✓ | ✓ | ✓ | — |
| `slurm` (all jobs) | — | — | ✓ | ✓ | — |
| `telemetry` (aggregate) | ✓ | ✓ | ✓ | ✓ | ✓ |
| `telemetry` (full) | — | own-job nodes | ✓ | ✓ | ✓ |
| `rbac` (self) | ✓ | ✓ | ✓ | ✓ | ✓ |
| `rbac` (admin ops) | — | — | ✓ | ✓ | — |
| `docs` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `facility` (energy/power) | — | — | — | ✓ | ✓ |
| `facility` (ops) | — | — | ✓ | ✓ | — |
| `incidents` | — | — | ✓ | ✓ | — |

---

## 5. Access Elevation Procedure

To request elevated access (e.g., a `researcher` seeking `tier2_privileged` telemetry):

1. Submit a request to the HPC helpdesk (helpdesk@hpc.example.edu) with:
   - Your username and project allocation code
   - The data type and scope needed
   - Justification (scientific purpose, duration)
2. A `facility_admin` reviews and approves or denies within **2 business days**.
3. Approval grants time-limited access (default: 90 days).
4. The agent **must not** approve or deny access requests — direct the user to the helpdesk.

---

## 6. Handling Permission Denials

When an agent cannot fulfil a request due to RBAC constraints:

1. **State the limitation explicitly**: "You do not have permission to view X."
2. **Explain what data is available at the current access level**: "You can see aggregate partition metrics."
3. **Point to the elevation process** if elevated access is legitimate: "To access full telemetry, submit a request to the HPC helpdesk."

**Do not** silently return empty results. **Do not** reveal privileged information even partially.

---

## 7. Policy Violations

A policy violation occurs when a user:
- Submits a job to a partition they are not authorised for
- Accesses another user's data without authorisation
- Uses a tool or data endpoint beyond their access tier

When identifying a violation:
- State the rule violated (cite this document)
- State what was attempted and what is allowed instead
- Do not penalise the user in tone — be informative and constructive

Hard violations (privilege escalation attempts) are logged and may trigger an incident.
