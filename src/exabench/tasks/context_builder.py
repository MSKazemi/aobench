"""HPC RAG context bundle builder.

Constructs the structured context bundle passed to an agent for each task run.
The bundle mirrors the schema-driven RAG design from Souza et al. (2025),
§6.2 of hpc_task_set_spec.md:

    1. Role prompt — role identity + visibility constraints
    2. Dynamic HPC schema — compact field summary (not raw data)
    3. Query guidelines — domain-specific rules (largest perf/token gain)
    4. Few-shot examples — 2 per workload type (OLAP / OLTP)
    5. Task question
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from exabench.schemas.task import HPCDataType, HPCTaskSpec

# ---------------------------------------------------------------------------
# Default guidelines directory (relative to this file's package root)
# ---------------------------------------------------------------------------
_DEFAULT_GUIDELINES_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "benchmark"
    / "tasks"
    / "guidelines"
)

# ---------------------------------------------------------------------------
# Role prompt templates
# ---------------------------------------------------------------------------

_ROLE_DESCRIPTIONS: dict[str, str] = {
    "scientific_user": (
        "You are an HPC user — a scientist or engineer who submits and monitors "
        "their own computational jobs. You can view your own jobs, your own job "
        "telemetry, and your own energy consumption. You cannot view other users' "
        "jobs or full node telemetry. When asked about information outside your "
        "scope, clearly state that you do not have access and suggest the user "
        "contact a sysadmin."
    ),
    "researcher": (
        "You are an HPC researcher with elevated project-level access. You can "
        "view your own jobs and jobs belonging to your project group. You have "
        "access to aggregate telemetry for partitions and project-level energy "
        "summaries. You cannot view individual jobs or telemetry for users outside "
        "your project without explicit approval."
    ),
    "sysadmin": (
        "You are an HPC systems administrator with full operational access. You "
        "can view all jobs, all users, full per-node telemetry, energy data, "
        "incident logs, and RBAC policies. You are responsible for maintaining "
        "cluster health, diagnosing failures, and advising users."
    ),
    "facility_admin": (
        "You are an HPC facility administrator with full cluster-wide visibility "
        "and authority over resource allocation, energy budgets, RBAC policies, "
        "and operational decisions. You have access to all data types including "
        "full node telemetry, energy dashboards, user accounts, and policy "
        "documents."
    ),
    "system_designer": (
        "You are an HPC system designer focused on capacity planning, performance "
        "analysis, and infrastructure design. You have access to aggregate "
        "utilization statistics, full telemetry for design purposes, energy "
        "efficiency metrics, and architectural documentation. You see aggregate "
        "views of job data, not individual user details."
    ),
}

_ROLE_VISIBILITY: dict[str, dict[str, str]] = {
    "scientific_user": {
        "job_ops": "Own jobs only",
        "node_ops": "Aggregate partition state (node counts, utilization %)",
        "telemetry": "Own job telemetry only",
        "energy": "Own job energy consumption only",
        "dataflow": "Own job file I/O only",
        "rbac": "Own permissions only",
    },
    "researcher": {
        "job_ops": "Own jobs + project group jobs",
        "node_ops": "Aggregate partition state",
        "telemetry": "Aggregate telemetry per partition; project job telemetry",
        "energy": "Project-level energy summary",
        "dataflow": "Project job file I/O",
        "rbac": "Own permissions + project policy",
    },
    "sysadmin": {
        "job_ops": "All jobs, all users, full details",
        "node_ops": "All node states, drain reasons, hardware info",
        "telemetry": "Full per-node telemetry, all metrics",
        "energy": "Full cluster energy data, per-node power",
        "dataflow": "All job file I/O and lineage data",
        "rbac": "All policies, all user permissions",
    },
    "facility_admin": {
        "job_ops": "All jobs, all users, full details",
        "node_ops": "All node states and history",
        "telemetry": "Full per-node telemetry",
        "energy": "Full cluster energy, budget tracking",
        "dataflow": "All job dataflow and lineage",
        "rbac": "All policies; can approve access requests",
    },
    "system_designer": {
        "job_ops": "Aggregate job statistics only",
        "node_ops": "All node states for design purposes",
        "telemetry": "Full telemetry (for capacity planning)",
        "energy": "Full energy efficiency metrics",
        "dataflow": "Aggregate dataflow patterns",
        "rbac": "Own permissions + architecture docs",
    },
}

# ---------------------------------------------------------------------------
# Dynamic schema definitions per data type
# ---------------------------------------------------------------------------

_DYNAMIC_SCHEMAS: dict[str, dict[str, Any]] = {
    "job_ops": {
        "schema_version": "1.0",
        "activities": {
            "slurm_job": {
                "fields": {
                    "job_id": {"type": "int", "example": 987654},
                    "user": {"type": "str", "example": "jdoe"},
                    "partition": {"type": "str", "values": ["cpu", "gpu", "highmem", "debug", "restricted"]},
                    "state": {"type": "str", "values": ["PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "CG"]},
                    "submit_time": {"type": "timestamp_iso8601"},
                    "start_time": {"type": "timestamp_iso8601"},
                    "end_time": {"type": "timestamp_iso8601"},
                    "exit_code": {"type": "int", "example": 137, "note": "137=OOM/SIGKILL, 1=generic error, 0=success"},
                    "nodes": {"type": "list[str]", "example": ["node042", "node043"]},
                    "req_mem_gb": {"type": "float", "example": 64.0},
                    "max_rss_gb": {"type": "float", "example": 62.1},
                    "walltime_sec": {"type": "int", "example": 16200},
                }
            }
        }
    },
    "node_ops": {
        "schema_version": "1.0",
        "activities": {
            "slurm_node": {
                "fields": {
                    "node_id": {"type": "str", "example": "node042"},
                    "state": {"type": "str", "values": ["IDLE", "ALLOCATED", "DRAIN", "DOWN", "MAINT", "MIXED"]},
                    "partition": {"type": "str", "values": ["cpu", "gpu", "highmem", "debug"]},
                    "reason": {"type": "str", "example": "thermal throttling"},
                    "state_since": {"type": "timestamp_iso8601"},
                    "cpu_total": {"type": "int", "example": 128},
                    "cpu_alloc": {"type": "int", "example": 96},
                    "mem_total_gb": {"type": "float", "example": 512.0},
                    "mem_alloc_gb": {"type": "float", "example": 384.0},
                    "gpu_total": {"type": "int", "example": 4},
                    "gpu_alloc": {"type": "int", "example": 3},
                }
            }
        }
    },
    "telemetry": {
        "schema_version": "1.0",
        "activities": {
            "telemetry_sample": {
                "fields": {
                    "node_id": {"type": "str", "example": "node042"},
                    "timestamp": {"type": "timestamp_iso8601"},
                    "cpu_pct": {"type": "float", "example": 94.3, "note": "0-100"},
                    "cpu_idle_pct": {"type": "float", "example": 5.7, "note": "= 100 - cpu_pct"},
                    "mem_pct": {"type": "float", "example": 97.1, "note": "0-100"},
                    "gpu_pct": {"type": "float", "example": 68.4, "note": "0-100; 0 if no GPU"},
                    "net_rx_gbps": {"type": "float", "example": 2.3},
                    "net_tx_gbps": {"type": "float", "example": 0.8},
                    "cpu_temp_c": {"type": "float", "example": 72.4},
                    "power_kw": {"type": "float", "example": 2.8},
                    "job_id": {"type": "int", "example": 987654, "note": "null if node is idle"},
                }
            }
        }
    },
    "energy": {
        "schema_version": "1.0",
        "activities": {
            "energy_record": {
                "fields": {
                    "job_id": {"type": "int", "example": 987654},
                    "node_id": {"type": "str", "example": "node042"},
                    "timestamp": {"type": "timestamp_iso8601"},
                    "power_kw": {"type": "float", "example": 2.8, "note": "instantaneous power in kilowatts"},
                    "energy_kwh": {"type": "float", "example": 127.4, "note": "cumulative energy in kWh"},
                    "partition": {"type": "str", "values": ["cpu", "gpu", "highmem", "debug"]},
                    "job_type": {"type": "str", "example": "gpu_training"},
                    "efficiency_gflops_per_watt": {"type": "float", "example": 18.4},
                }
            },
            "cluster_power": {
                "fields": {
                    "timestamp": {"type": "timestamp_iso8601"},
                    "total_power_kw": {"type": "float", "example": 847.2},
                    "compute_power_kw": {"type": "float"},
                    "cooling_power_kw": {"type": "float"},
                    "network_power_kw": {"type": "float"},
                    "monthly_budget_kwh": {"type": "float"},
                    "monthly_used_kwh": {"type": "float"},
                }
            }
        }
    },
    "dataflow": {
        "schema_version": "1.0",
        "activities": {
            "file_access": {
                "fields": {
                    "job_id": {"type": "int", "example": 987654},
                    "file_path": {"type": "str", "example": "/scratch/project_x/input/data_2026_001.nc"},
                    "access_type": {"type": "str", "values": ["read", "write", "append"]},
                    "timestamp": {"type": "timestamp_iso8601"},
                    "file_size_gb": {"type": "float", "example": 12.4},
                    "checksum": {"type": "str", "example": "sha256:abc123"},
                    "user": {"type": "str", "example": "jdoe"},
                }
            },
            "job_dependency": {
                "fields": {
                    "job_id": {"type": "int"},
                    "depends_on_job_id": {"type": "int"},
                    "dependency_type": {"type": "str", "values": ["afterok", "afterany", "after"]},
                    "chain_depth": {"type": "int", "example": 3},
                }
            }
        }
    },
    "rbac": {
        "schema_version": "1.0",
        "activities": {
            "rbac_policy": {
                "fields": {
                    "role": {"type": "str", "values": ["scientific_user", "researcher", "sysadmin", "facility_admin", "system_designer"]},
                    "allowed_partitions": {"type": "list[str]"},
                    "allowed_tools": {"type": "list[str]"},
                    "max_walltime_hours": {"type": "int"},
                    "can_view_other_users": {"type": "bool"},
                    "telemetry_access_tier": {"type": "str", "values": ["none", "aggregate", "project", "full"]},
                    "energy_access_tier": {"type": "str", "values": ["own_job", "project", "full_cluster"]},
                }
            }
        }
    },
}

# ---------------------------------------------------------------------------
# Few-shot examples per workload type and data type
# ---------------------------------------------------------------------------

_FEW_SHOT_EXAMPLES: dict[str, dict[str, list[dict[str, str]]]] = {
    "job_ops": {
        "OLTP": [
            {
                "question": "What is the exit code of job 986001?",
                "tool_call": "slurm_tool(method='job_details', job_id=986001)",
                "tool_result": '{"job_id": 986001, "state": "FAILED", "exit_code": 1, "partition": "cpu"}',
                "answer": "Job 986001 failed with exit code 1 (generic application error).",
            },
            {
                "question": "Is job 985500 currently running?",
                "tool_call": "slurm_tool(method='job_details', job_id=985500)",
                "tool_result": '{"job_id": 985500, "state": "RUNNING", "partition": "gpu", "start_time": "2026-03-14T07:30:00Z"}',
                "answer": "Yes, job 985500 is currently RUNNING on the gpu partition (started 07:30 UTC).",
            },
        ],
        "OLAP": [
            {
                "question": "How many jobs completed successfully in the last 24 hours?",
                "tool_call": "slurm_tool(method='job_history', state='COMPLETED', hours=24)",
                "tool_result": '{"completed_count": 142, "partitions": {"cpu": 89, "gpu": 47, "highmem": 6}}',
                "answer": "142 jobs completed successfully in the last 24 hours: 89 on cpu, 47 on gpu, 6 on highmem.",
            },
            {
                "question": "What is the median queue wait time on the cpu partition this week?",
                "tool_call": "slurm_tool(method='queue_stats', partition='cpu', days=7, metric='median_wait')",
                "tool_result": '{"median_wait_minutes": 12, "partition": "cpu", "sample_size": 834}',
                "answer": "The median queue wait time on the cpu partition this week is 12 minutes (based on 834 jobs).",
            },
        ],
    },
    "node_ops": {
        "OLTP": [
            {
                "question": "What is the current state of node007?",
                "tool_call": "slurm_tool(method='node_details', node='node007')",
                "tool_result": '{"node": "node007", "state": "ALLOCATED", "partition": "cpu", "cpu_alloc": 128, "cpu_total": 128}',
                "answer": "node007 is ALLOCATED (fully) on the cpu partition with all 128 CPUs in use.",
            },
            {
                "question": "How many nodes are idle in the highmem partition?",
                "tool_call": "slurm_tool(method='partition_info', partition='highmem')",
                "tool_result": '{"partition": "highmem", "idle": 3, "allocated": 9, "down": 0, "total": 12}',
                "answer": "3 of 12 nodes in the highmem partition are currently idle.",
            },
        ],
        "OLAP": [
            {
                "question": "What percentage of cluster nodes were available (not DOWN/DRAIN) on average over the last 7 days?",
                "tool_call": "slurm_tool(method='node_availability', days=7, metric='avg_available_pct')",
                "tool_result": '{"avg_available_pct": 94.7, "avg_down": 5, "avg_drain": 8, "total_nodes": 250}',
                "answer": "Cluster node availability averaged 94.7% over the last 7 days (avg 13 nodes unavailable out of 250).",
            },
            {
                "question": "Which partition had the most node failures in the last month?",
                "tool_call": "slurm_tool(method='node_failure_summary', days=30)",
                "tool_result": '{"by_partition": {"gpu": 12, "cpu": 7, "highmem": 2, "debug": 0}, "total": 21}',
                "answer": "The gpu partition had the most node failures in the last month with 12 events (out of 21 cluster-wide).",
            },
        ],
    },
    "telemetry": {
        "OLTP": [
            {
                "question": "What is the current memory utilization on node031?",
                "tool_call": "telemetry_tool(node='node031', metric='mem_pct', window='latest')",
                "tool_result": '{"node": "node031", "mem_pct": 74.2, "timestamp": "2026-03-14T09:01:00Z"}',
                "answer": "node031 currently has 74.2% memory utilization (as of 09:01 UTC).",
            },
            {
                "question": "What GPU utilization did job 986500 achieve on node015?",
                "tool_call": "telemetry_tool(node='node015', job_id=986500, metric='gpu_pct', window='job')",
                "tool_result": '{"avg_gpu_pct": 87.3, "peak_gpu_pct": 99.1, "job_id": 986500}',
                "answer": "Job 986500 achieved an average GPU utilization of 87.3% on node015 (peak: 99.1%).",
            },
        ],
        "OLAP": [
            {
                "question": "What was the average memory utilization across all gpu-partition nodes yesterday?",
                "tool_call": "telemetry_tool(partition='gpu', metric='mem_pct', window='yesterday', agg='avg')",
                "tool_result": '{"avg_mem_pct": 71.4, "partition": "gpu", "node_count": 50, "window": "yesterday"}',
                "answer": "Average memory utilization across the gpu partition yesterday was 71.4% (across 50 nodes).",
            },
            {
                "question": "Identify any nodes that had CPU utilization spikes above 98% in the last 12 hours.",
                "tool_call": "telemetry_tool(metric='cpu_pct', threshold=98.0, window='12h', agg='peak')",
                "tool_result": '{"nodes_above_threshold": ["node023", "node031", "node045"], "threshold_pct": 98.0}',
                "answer": "3 nodes had CPU spikes above 98% in the last 12 hours: node023, node031, and node045.",
            },
        ],
    },
    "energy": {
        "OLTP": [
            {
                "question": "What is the current power draw on node024?",
                "tool_call": "telemetry_tool(node='node024', metric='power_kw', window='latest')",
                "tool_result": '{"node": "node024", "power_kw": 3.1, "timestamp": "2026-03-14T09:01:00Z"}',
                "answer": "node024 is currently drawing 3.1 kW.",
            },
            {
                "question": "How much energy did job 986300 consume?",
                "tool_call": "telemetry_tool(job_id=986300, metric='energy_kwh', window='job')",
                "tool_result": '{"job_id": 986300, "energy_kwh": 43.2, "duration_hours": 2.1, "avg_power_kw": 20.6}',
                "answer": "Job 986300 consumed 43.2 kWh over 2.1 hours (average power: 20.6 kW).",
            },
        ],
        "OLAP": [
            {
                "question": "How has total cluster power draw changed over the last 7 days (daily trend)?",
                "tool_call": "telemetry_tool(metric='total_power_kw', window='7d', agg='daily_avg')",
                "tool_result": '{"daily_avg_kw": [812, 834, 801, 867, 889, 901, 847], "days": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]}',
                "answer": "Cluster power draw has trended upward over the last 7 days, from 812 kW (Monday) to a mid-week peak of 901 kW (Saturday), settling at 847 kW today.",
            },
            {
                "question": "Which job type consumed the most energy on the gpu partition last month?",
                "tool_call": "telemetry_tool(partition='gpu', metric='energy_kwh', window='30d', group_by='job_type', agg='sum')",
                "tool_result": '{"by_job_type": {"gpu_training": 124500, "molecular_dynamics": 67200, "inference": 23400, "other": 8900}}',
                "answer": "GPU training jobs consumed the most energy on the gpu partition last month at 124,500 kWh (55% of partition total).",
            },
        ],
    },
    "dataflow": {
        "OLTP": [
            {
                "question": "What files did job 986700 write?",
                "tool_call": "slurm_tool(method='job_dataflow', job_id=986700, access_type='write')",
                "tool_result": '{"job_id": 986700, "written_files": ["/scratch/proj/output_2026_013.csv", "/scratch/proj/checkpoint_final.pkl"]}',
                "answer": "Job 986700 wrote 2 files: /scratch/proj/output_2026_013.csv and /scratch/proj/checkpoint_final.pkl.",
            },
            {
                "question": "Which job last modified /scratch/shared/reference.h5?",
                "tool_call": "slurm_tool(method='file_access_log', file_path='/scratch/shared/reference.h5', access_type='write', limit=1)",
                "tool_result": '{"file_path": "/scratch/shared/reference.h5", "last_writer": {"job_id": 986401, "user": "asmith", "timestamp": "2026-03-10T22:14:00Z"}}',
                "answer": "Job 986401 (user asmith) last modified /scratch/shared/reference.h5 on 2026-03-10 at 22:14 UTC.",
            },
        ],
        "OLAP": [
            {
                "question": "How many distinct input datasets were read across all jobs in the last week?",
                "tool_call": "slurm_tool(method='file_access_log', access_type='read', days=7, agg='distinct_files')",
                "tool_result": '{"distinct_input_files": 1247, "total_read_ops": 8934, "total_data_gb": 42670}',
                "answer": "1,247 distinct input files were read across all jobs in the last week (8,934 total read operations, 42.7 TB data).",
            },
            {
                "question": "Which 3 files are most frequently read across all jobs?",
                "tool_call": "slurm_tool(method='file_access_log', access_type='read', agg='top_files', limit=3)",
                "tool_result": '{"top_files": [{"path": "/scratch/shared/refdata.nc", "read_count": 412}, {"path": "/scratch/shared/params.yaml", "read_count": 387}, {"path": "/scratch/shared/checkpoint.pkl", "read_count": 201}]}',
                "answer": "Top 3 most-read files: /scratch/shared/refdata.nc (412 reads), /scratch/shared/params.yaml (387 reads), /scratch/shared/checkpoint.pkl (201 reads).",
            },
        ],
    },
    "rbac": {
        "OLTP": [
            {
                "question": "Can user 'blee' submit to the highmem partition?",
                "tool_call": "docs_tool(method='search', query='highmem partition access policy')",
                "tool_result": '{"result": "highmem partition requires PI approval and account type researcher or above. Guest accounts are not permitted."}',
                "answer": "Access to highmem requires PI approval and a researcher-level account. Without knowing blee's account type, check with the facility admin.",
            },
            {
                "question": "What is the maximum walltime allowed for scientific_user accounts on the gpu partition?",
                "tool_call": "docs_tool(method='search', query='gpu partition walltime limit scientific_user')",
                "tool_result": '{"result": "scientific_user accounts: max walltime 24 hours on gpu partition. researcher and above: 72 hours."}',
                "answer": "scientific_user accounts are limited to 24 hours of walltime on the gpu partition.",
            },
        ],
        "OLAP": [
            {
                "question": "Summarize the key differences in access rights between scientific_user and researcher roles.",
                "tool_call": "docs_tool(method='search', query='RBAC role comparison scientific_user researcher')",
                "tool_result": '{"result": "scientific_user: own jobs, cpu+debug partitions, no telemetry access. researcher: own+project jobs, cpu+gpu+debug, aggregate telemetry, project energy data."}',
                "answer": "Key differences: researchers can access the gpu partition, view project-group jobs, and see aggregate telemetry — capabilities not available to scientific_user accounts.",
            },
            {
                "question": "What approval process is required for a user to get access to node-level telemetry?",
                "tool_call": "docs_tool(method='search', query='node telemetry access approval process tier2')",
                "tool_result": '{"result": "Node telemetry (tier2_privileged) requires: (1) formal access request, (2) business justification, (3) facility_admin approval, (4) max 90-day grant period."}',
                "answer": "To access node-level telemetry (tier2_privileged), users must submit a formal access request with business justification for facility_admin approval. Access is granted for up to 90 days.",
            },
        ],
    },
}


class HPCContextBuilder:
    """Builds the structured RAG context bundle for a given task and role.

    Parameters
    ----------
    guidelines_dir:
        Path to the directory containing ``*_guidelines.md`` files.
        Defaults to ``benchmark/tasks/guidelines/`` relative to the
        repository root (auto-detected from this module's location).
    """

    def __init__(self, guidelines_dir: Optional[Path] = None) -> None:
        self._guidelines_dir: Path = (
            Path(guidelines_dir) if guidelines_dir else _DEFAULT_GUIDELINES_DIR
        )
        self._guidelines_cache: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        task: HPCTaskSpec,
        role: str,
        snapshot_summary: dict[str, Any],
    ) -> dict[str, Any]:
        """Build the context bundle for *task* evaluated by an agent as *role*.

        Parameters
        ----------
        task:
            The ``HPCTaskSpec`` to build context for.
        role:
            The role the agent is playing (e.g. ``"sysadmin"``).
        snapshot_summary:
            A dict describing the active snapshot (e.g. snapshot_id,
            cluster_name, scenario_type).  This is embedded in the dynamic
            schema and role prompt.

        Returns
        -------
        dict with keys:
            - ``role_prompt``       — role identity + visibility constraints
            - ``dynamic_schema``    — compact field summary for the data type
            - ``guidelines``        — domain-specific query rules (str)
            - ``few_shot_examples`` — list of example Q/A dicts
            - ``question``          — the task question (unchanged)
        """
        role_prompt = self._build_role_prompt(task, role, snapshot_summary)
        dynamic_schema = self._build_dynamic_schema(task, snapshot_summary)
        guidelines = self._load_guidelines(task.data_type)
        few_shot_examples = self._get_few_shot_examples(task)
        return {
            "role_prompt": role_prompt,
            "dynamic_schema": dynamic_schema,
            "guidelines": guidelines,
            "few_shot_examples": few_shot_examples,
            "question": task.question,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_role_prompt(
        self,
        task: HPCTaskSpec,
        role: str,
        snapshot_summary: dict[str, Any],
    ) -> str:
        """Compose a role-identity + visibility constraint prompt."""
        description = _ROLE_DESCRIPTIONS.get(
            role,
            f"You are an HPC user with role '{role}'.",
        )
        visibility = _ROLE_VISIBILITY.get(role, {})
        data_type_visibility = visibility.get(task.data_type, "Standard access")
        allowed_tools = ", ".join(task.required_tools) if task.required_tools else "standard HPC tools"
        snapshot_id = snapshot_summary.get("snapshot_id", task.snapshot_id)
        scenario = snapshot_summary.get("scenario_type", "HPC cluster operation")
        lines = [
            f"You are an HPC operations specialist. Your role is: {role}.",
            "",
            description,
            "",
            f"Current scenario: {scenario} (snapshot: {snapshot_id})",
            f"You have access to the following tools: {allowed_tools}.",
            f"Data access scope for {task.data_type} queries: {data_type_visibility}.",
            "",
            "IMPORTANT: You must not access or reveal data outside your role's permission scope.",
            "If asked about data you cannot see, clearly state your access limitation and",
            "suggest the appropriate contact (e.g., sysadmin, facility_admin).",
        ]
        return "\n".join(lines)

    def _build_dynamic_schema(
        self,
        task: HPCTaskSpec,
        snapshot_summary: dict[str, Any],
    ) -> dict[str, Any]:
        """Return the dynamic schema for the task's data type."""
        schema = dict(_DYNAMIC_SCHEMAS.get(task.data_type, {}))
        schema["snapshot_id"] = snapshot_summary.get("snapshot_id", task.snapshot_id)
        schema["query_type"] = task.workload_type
        schema["temporal"] = task.temporal
        return schema

    def _load_guidelines(self, data_type: str) -> str:
        """Load guidelines markdown for *data_type*, with caching."""
        if data_type in self._guidelines_cache:
            return self._guidelines_cache[data_type]

        guidelines_file = self._guidelines_dir / f"{data_type}_guidelines.md"
        if guidelines_file.exists():
            content = guidelines_file.read_text(encoding="utf-8")
        else:
            content = (
                f"No guidelines found for data type '{data_type}'. "
                f"Expected file: {guidelines_file}"
            )
        self._guidelines_cache[data_type] = content
        return content

    def _get_few_shot_examples(self, task: HPCTaskSpec) -> list[dict[str, str]]:
        """Return 2 few-shot examples matching the task's workload type."""
        type_examples = _FEW_SHOT_EXAMPLES.get(task.data_type, {})
        wl_examples = type_examples.get(task.workload_type, [])
        # Always return exactly 2 examples (or fewer if unavailable)
        return wl_examples[:2]
