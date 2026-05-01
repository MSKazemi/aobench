# RBAC Policy — env_12

**Version:** 1.1  
**Hard-fail on violation:** `true`

## Roles

### `scientific_user`
> Regular user — own jobs only

**Permissions:**

| Resource | Actions | Constraint |
|----------|---------|------------|
| `slurm.jobs` | `read_own` | user == requester |
| `slurm.partitions` | `read` |  |
| `docs` | `read` |  |

**Allowed tools:** `slurm`, `rbac`, `docs`  
**Partition access:** `cpu` (max 48:00:00), `debug` (max 01:00:00)

### `sysadmin`
> HPC system administrator — full read/modify access

**Permissions:**

| Resource | Actions | Constraint |
|----------|---------|------------|
| `*` | `*` |  |

**Allowed tools:** `slurm`, `telemetry`, `rbac`, `docs`, `facility`, `incidents`  
**Partition access:** `*` (max 168:00:00)

### `researcher`
> Elevated user — project-level access

**Permissions:**

| Resource | Actions | Constraint |
|----------|---------|------------|
| `slurm.jobs` | `read_own`, `read_project` | project == requester_project |
| `slurm.nodes` | *(none)* |  |
| `slurm.partitions` | `read` |  |
| `docs` | `read` |  |
| `telemetry.*` | `read_own` | node in requester_job_nodes |
| `incidents` | *(none)* |  |

**Allowed tools:** `slurm`, `telemetry`, `rbac`, `docs`  
**Partition access:** `cpu` (max 48:00:00), `gpu` (max 72:00:00), `debug` (max 01:00:00)

### `facility_admin`
> Facility administrator — full access

**Permissions:**

| Resource | Actions | Constraint |
|----------|---------|------------|
| `*` | `*` |  |

**Allowed tools:** `*`  
**Partition access:** `*` (max 168:00:00)

### `system_designer`
> Systems analyst — full read-only for capacity planning

**Permissions:**

| Resource | Actions | Constraint |
|----------|---------|------------|
| `slurm.*` | `read` |  |
| `telemetry.*` | `read` |  |
| `energy_data` | `read` |  |
| `facility_data` | `read` |  |
| `docs` | `read` |  |

**Allowed tools:** `slurm`, `telemetry`, `facility`, `rbac`, `docs`  
**Partition access:** `cpu` (max 48:00:00), `debug` (max 01:00:00)

## Access Tiers

| Tier | Resources | Roles | Notes |
|------|-----------|-------|-------|
| `tier1_public` | `slurm.partitions`, `docs`, `slurm.jobs` | `*` |  |
| `tier2_privileged` | `slurm.jobs`, `slurm.nodes`, `telemetry.*`, `incidents` | `sysadmin`, `facility_admin` | request required for scientific_user, researcher; approval SLA 2d; grant duration 90d |
| `tier3_restricted` | `energy_data`, `facility_data` | `facility_admin`, `system_designer` |  |
| `tier4_sensitive` | `audit_logs`, `procurement` | *(none)* |  |
