# RBAC and Policy Query Guidelines

These guidelines apply to all `rbac` queries covering role-based access control,
partition policies, and permission decisions.

## Role Hierarchy

1. **Role access levels (lowest to highest privilege):**
   `scientific_user` < `researcher` < `sysadmin` / `facility_admin` < `system_designer` (design scope only).
   A role can access everything its lower-privilege roles can, plus additional
   capabilities defined in the policy document. Never grant access above the
   querying role's tier.

2. **sysadmin** and **facility_admin** are both privileged roles but have
   different scopes: sysadmin focuses on operational access (jobs, nodes,
   incidents); facility_admin has authority over budget, policy enforcement,
   and access approvals. Both have full data visibility.

## Partition Access Policy

3. **Partition access by role:**
   - `scientific_user`: `cpu`, `debug` only
   - `researcher`: `cpu`, `gpu`, `debug`
   - `sysadmin`: all partitions (`cpu`, `gpu`, `highmem`, `debug`, `restricted`)
   - `facility_admin`: all partitions
   - `system_designer`: `cpu`, `debug` (production partitions require approval)
   Always check the active RBAC policy document — these defaults may be
   overridden by project-level grants or time-limited approvals.

## Answering Permission Questions

4. **When a user asks "Can I see X?"**: Look up their role's access tier for
   data type X, then give a clear Yes/No answer followed by:
   - If Yes: what they can see and at what granularity
   - If No: what they *can* see instead, and how to request elevated access

5. **Role-filtered answers**: For `rbac_01`-style questions ("What can I do?"),
   the answer is role-specific. Never give a generic answer that includes
   capabilities the querying role does not have. The agent must substitute
   the actual role when generating the answer.

## Access Tier Definitions

6. **Access tiers for telemetry and data:**
   - `tier1_public` — aggregate stats, available to all roles without approval
   - `tier2_privileged` — per-node telemetry, full job details; requires
     formal request + facility_admin approval (granted for up to 90 days)
   - `tier3_restricted` — energy dashboards, billing data; facility_admin only
   - `tier4_sensitive` — security logs, audit trails; requires explicit grant

## Policy Advice Responses

7. **When advising on access requests**, always:
   (a) State the relevant policy section/rule
   (b) Describe the formal process (form, justification, approver)
   (c) State the typical approval timeline (e.g., 2 business days)
   (d) Suggest whether a lower-tier alternative might meet the need
   Do not approve or deny access requests in the answer — direct to the
   appropriate approver (facility_admin).

## RBAC Violation Detection

8. **Policy violations** occur when a user submits to a partition they are
   not authorized for, attempts to access another user's data, or uses tools
   beyond their access tier. When identifying a violation:
   - State the rule that was violated (policy section)
   - State what the user attempted
   - State what they are allowed to do instead
   Do not punish the user in the answer — be informative and constructive.

## Explaining Limitations

9. **When an agent cannot fulfill a request due to RBAC constraints**, the
   response should:
   (1) Clearly state the limitation ("You do not have permission to view X")
   (2) Explain what access level is needed
   (3) Point to the request process if elevated access is legitimate
   Never silently return empty results — always explain why data is withheld.

## Policy Document Lookup

10. **Always ground RBAC answers in the policy document** retrieved via
    `docs_tool`. Do not answer from memory alone — RBAC rules may differ
    between snapshots or have been updated. Quote the relevant policy
    section when giving authoritative answers on permissions.
