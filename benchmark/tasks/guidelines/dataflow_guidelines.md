# Dataflow and Provenance Query Guidelines

These guidelines apply to all `dataflow` queries covering file I/O provenance,
data lineage, and job dependency chains.

## File Path Conventions

1. **File paths are absolute POSIX paths** starting with `/scratch/` for
   job data or `/home/` for user configuration files. Always report full
   paths — do not abbreviate with `~` or relative paths. When listing
   multiple files, report one per line.

2. **File access types:** `read` (input), `write` (output/created),
   `append` (modified). A single job may both read and write the same file
   (checkpoint/restart patterns). Always report the access type alongside
   the file path.

## Job I/O Lookup

3. **To find input/output files for a job**, use
   `slurm_tool(method='job_dataflow', job_id=<id>)`. This returns both
   `read_files` and `written_files` lists. For partial jobs (failed/OOM),
   note that output files may be incomplete.

4. **Partial outputs**: If a job failed (exit code ≠ 0), output files may
   exist but be incomplete. Always note this when reporting output files for
   failed jobs: *"Output may be partial — job terminated with exit code 137."*

## Data Lineage Tracing

5. **Data lineage** traces the provenance chain: which jobs produced or
   transformed a given file. Build the lineage graph by: (1) find the job
   that wrote the target file, (2) find that job's input files, (3) find
   jobs that wrote those inputs, and recurse. Report the full chain with
   job IDs, transformations, and timestamps.

6. **Lineage graph depth** is the number of hops from the root input
   (original raw data) to the target file. Report depth explicitly:
   *"Data lineage spans 2 jobs, depth 3."*

## File Access History

7. **For queries about who read a specific directory**, use the `file_path`
   prefix matching: `slurm_tool(method='file_access_log', file_path='/scratch/project_x/input/', prefix_match=True)`.
   Results include job_id, user, access_time, and access_type.

## Role Visibility for Dataflow

8. **scientific_user**: Only their own job's file I/O. Cannot see other
   users' file access patterns.
   **researcher**: Own jobs + project group jobs' file I/O.
   **sysadmin / facility_admin**: All jobs' file access across all users.
   When a scientific_user asks about files accessed by other users' jobs,
   decline and redirect to the sysadmin.

## Dependency Chains

9. **Job dependency chain depth** is the length of the longest path in the
   directed dependency graph rooted at the job. A job with no dependencies
   has depth 1. Report chain depth alongside the job IDs at each level.
   Deep chains (depth > 5) indicate complex workflows that are sensitive
   to upstream failures.

## Temporal Ordering

10. **For provenance queries**, always establish temporal ordering of the
    lineage chain using `end_time` of producer jobs and `start_time` of
    consumer jobs. A producer's `end_time` must precede the consumer's
    `start_time`. If this constraint is violated, flag it as a potential
    data integrity issue.
