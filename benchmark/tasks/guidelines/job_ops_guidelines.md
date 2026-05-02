# Job Operations Query Guidelines

These guidelines apply to all `job_ops` queries against SLURM job data.
Following these rules is the single largest factor in achieving accurate answers.

## Primary Key and Lookup

1. **Use `job_id` as the primary key** for all job lookups. Never use job name
   or user as a primary key — multiple jobs may share a name or belong to the
   same user.

2. **Job IDs are integers** (e.g., `987654`). Do not quote them as strings when
   passing to tool methods that expect numeric input.

## Job State Values

3. **Valid SLURM job states are:** `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`,
   `CANCELLED`, `TIMEOUT`, `CG` (completing), `NODE_FAIL`, `OUT_OF_MEMORY`.
   Always report the exact state string — do not paraphrase (e.g., do not say
   "finished" when the state is `COMPLETED`).

4. **Exit code semantics:**
   - `0` → success
   - `1` → generic application error
   - `137` → killed by OOM killer (SIGKILL; job exceeded memory limit)
   - `139` → segmentation fault (SIGSEGV)
   - `271` → SLURM timeout (job exceeded walltime)
   Always include the exit code when reporting a failed job.

## Time Fields

5. **Job time fields:** `submit_time`, `start_time`, `end_time` are ISO 8601
   timestamps (UTC). Queue wait time = `start_time − submit_time`. Walltime =
   `end_time − start_time`. Report durations in hours and minutes
   (e.g., "2 hours 34 minutes"), not raw seconds.

6. **For time-range queries** (e.g., "in the last 24 hours"), filter on
   `end_time` for completed/failed jobs and on `submit_time` for pending jobs.

## Role Visibility

7. **scientific_user** accounts can only see their own jobs. If a scientific_user
   asks about another user's jobs, respond: *"You do not have permission to view
   other users' jobs."* Do not reveal any details of other users' jobs.
   **researcher** accounts can see their own jobs and aggregate statistics for
   their project group; they cannot see individual jobs of other users.

8. **sysadmin**, **facility_admin**, and **system_designer** accounts can see
   all jobs across all users and partitions, including full detail (exit codes,
   node lists, RSS). system_designer access is scoped to capacity-planning
   purposes — do not expose per-user billing or sensitive audit data.

## Partition Names

9. **Valid partition names are:** `cpu`, `gpu`, `highmem`, `debug`, `restricted`.
   Always use the exact partition name. If a user mentions a partition that does
   not exist, note the error and list valid partitions.

## Aggregation Queries

10. **For OLAP queries** (count, average, trend), always state the time window
    and the number of records included in the aggregation. For example:
    *"Based on 834 jobs over the last 7 days..."*
