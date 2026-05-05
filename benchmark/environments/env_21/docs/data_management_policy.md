# Data Management Policy — AOBench Cluster A

## 1. Scratch Space Retention
Scratch filesystem (`/lustre/scratch`) has a **90-day retention window** for files not accessed within that period. Files exceeding quota grace periods (5 days) are subject to automatic archival to cold storage.

## 2. Project Quotas
| Tier | Quota | Grace Period |
|---|---|---|
| Standard project | 15 TB | 5 days |
| Priority project | 20 TB | 5 days |
| Emergency extension | +5 TB (90-day max) | Requires admin approval |

## 3. User Quotas
Default user scratch quota: 200 GB. Requests for higher quotas require project PI approval and sysadmin provisioning.

## 4. Archival & Backup
- Scratch: NOT backed up. Users responsible for staging critical data to `/home` or archive.
- Home: Daily incremental, weekly full backup (90-day retention).
- Archive (`/archive`): Write-once, 7-year retention, WORM-compliant.

## 5. Compliance
Data containing patient or personal identifiable information (PII) must reside only on `tier4_sensitive` designated filesystems. Violation triggers immediate account suspension.
