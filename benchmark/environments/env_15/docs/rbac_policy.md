# RBAC Policy — env_15

**Version:** 1.1  
**Hard-fail on violation:** `true`

## Roles

### `researcher`
> Researcher — own jobs and read-only telemetry

**Permissions:**

| Resource | Actions | Constraint |
|----------|---------|------------|
| `slurm.jobs` | `read_own` | user == requester |
| `slurm.partitions` | `read` |  |
| `telemetry.*` | `read` |  |
| `docs` | `read` |  |

**Allowed tools:** `slurm`, `telemetry`, `rbac`, `docs`  
**Partition access:** `cpu` (max 48:00:00), `gpu` (max 72:00:00), `debug` (max 01:00:00)

### `sysadmin`
> System administrator — full access

**Permissions:**

| Resource | Actions | Constraint |
|----------|---------|------------|
| `*` | `*` |  |

**Allowed tools:** `slurm`, `telemetry`, `rbac`, `docs`, `facility`, `incidents`  
**Partition access:** `*` (max 168:00:00)

### `scientific_user`
> HPC user — can view their own jobs only

**Permissions:**

| Resource | Actions | Constraint |
|----------|---------|------------|
| `slurm.jobs` | `read_own` | user == requester |
| `slurm.partitions` | `read` |  |
| `docs` | `read` |  |
| `telemetry.memory_events` | `read_own` | job_id in requester_jobs |
| `incidents` | *(none)* |  |

**Allowed tools:** `slurm`, `rbac`, `docs`  
**Partition access:** `cpu` (max 48:00:00), `debug` (max 01:00:00)

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
