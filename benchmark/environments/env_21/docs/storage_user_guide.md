# Storage User Guide — ExaBench Cluster A

## Checking Your Quota
Run `lfs quota -u $USER /lustre/scratch` to see your current usage and quota limits.

## I/O Best Practices for Large Parallel Jobs
1. **Use Lustre striping**: Set stripe count to the number of OSTs you will use: `lfs setstripe -c 8 /lustre/scratch/mydir`
2. **Avoid small files**: Consolidate many small files into HDF5 or tar archives to reduce metadata overhead.
3. **Collective I/O**: Use MPI-IO collective operations (e.g. `MPI_File_write_all`) for parallel writes.
4. **Stage data locally**: For I/O-intensive jobs, stage input data to `$TMPDIR` (local NVMe) at job start.

## Transferring Data
Use `globus-cli` for large transfers to/from external sites. For on-cluster transfers use `rsync` with `--partial --progress`.
