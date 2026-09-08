"""aobench rbac — RBAC policy management for customer governance profiler runs."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import typer
import yaml

rbac_app = typer.Typer(help="Manage RBAC policy ingestion for customer governance profiler runs.")


@rbac_app.command("ingest")
def rbac_ingest(
    policy: Annotated[str, typer.Option("--policy", "-p", help="Path to customer RBAC policy YAML file")],
    base_env: Annotated[str, typer.Option("--base-env", help="Base environment ID to clone from")] = "env_01",
    env_id: Annotated[str | None, typer.Option("--env-id", help="New environment ID (default: env_rbac_<timestamp>)")] = None,
    benchmark_root: Annotated[str, typer.Option("--benchmark", help="Path to benchmark/ directory")] = "benchmark",
) -> None:
    """Ingest a customer RBAC policy into a new environment bundle.

    Creates a clone of --base-env with the customer's RBAC policy replacing
    the default one. The resulting environment can be used to run the governance
    profiler against the customer's specific RBAC configuration.

    Use --no-langfuse on the subsequent run command to keep RBAC policy data local.

    Example:
        aobench rbac ingest --policy customer_rbac.yaml
        AOBENCH_SKIP_FIDELITY=1 uv run aobench run all \\
            --split dev --adapter openai:gpt-4o --no-langfuse
        uv run aobench report governance data/runs/<run_id>
    """
    policy_path = Path(policy)
    if not policy_path.exists():
        typer.echo(f"Error: RBAC policy file not found: {policy_path}", err=True)
        raise typer.Exit(1)

    # Validate the policy YAML is parseable
    try:
        with policy_path.open(encoding="utf-8") as f:
            policy_data = yaml.safe_load(f)
        if not isinstance(policy_data, dict):
            typer.echo("Error: RBAC policy must be a YAML mapping.", err=True)
            raise typer.Exit(1)
        if "roles" not in policy_data:
            typer.echo("Warning: RBAC policy has no 'roles' key — verify format matches rbac_policy.yaml schema.")
    except yaml.YAMLError as e:
        typer.echo(f"Error: Invalid YAML in policy file: {e}", err=True)
        raise typer.Exit(1)

    from aobench.cli._common import resolve_bundle_root

    benchmark_dir = resolve_bundle_root(benchmark_root)
    envs_dir = benchmark_dir / "environments"
    base_env_dir = envs_dir / base_env
    if not base_env_dir.is_dir():
        typer.echo(f"Error: Base environment not found: {base_env_dir}", err=True)
        raise typer.Exit(1)

    # Determine new environment ID
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    new_env_id = env_id or f"env_rbac_{timestamp}"

    new_env_dir = envs_dir / new_env_id
    if new_env_dir.exists():
        typer.echo(f"Error: Environment directory already exists: {new_env_dir}", err=True)
        raise typer.Exit(1)

    # Clone base environment
    typer.echo(f"Cloning {base_env} → {new_env_id}...")
    shutil.copytree(base_env_dir, new_env_dir)

    # Replace RBAC policy
    rbac_policy_dest = new_env_dir / "policy" / "rbac_policy.yaml"
    rbac_policy_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(policy_path, rbac_policy_dest)
    typer.echo(f"RBAC policy installed: {rbac_policy_dest}")

    # Update metadata.yaml with new environment ID
    metadata_path = new_env_dir / "metadata.yaml"
    with metadata_path.open(encoding="utf-8") as f:
        metadata = yaml.safe_load(f)

    metadata["environment_id"] = new_env_id
    metadata["bundle_root"] = f"environments/{new_env_id}"
    metadata["snapshot_name"] = f"Custom RBAC policy (cloned from {base_env})"
    metadata["snapshot_timestamp"] = datetime.now(tz=timezone.utc).isoformat()
    metadata["implementation_status"] = "bundled"
    metadata["validation_status"] = "not_checked"
    metadata["description"] = (
        f"Custom RBAC policy bundle cloned from {base_env}. "
        f"Source policy: {policy_path.name}. "
        "Use AOBENCH_SKIP_FIDELITY=1 when running benchmark tasks against this bundle."
    )

    with metadata_path.open("w", encoding="utf-8") as f:
        yaml.dump(metadata, f, default_flow_style=False, allow_unicode=True)

    typer.echo(f"Metadata updated: environment_id = {new_env_id}")

    # Validate the new bundle loads correctly (skip fidelity)
    import os
    os.environ["AOBENCH_SKIP_FIDELITY"] = "1"
    try:
        from aobench.loaders.env_loader import load_environment
        load_environment(new_env_dir)
        typer.echo("Bundle validation: passed")
    except Exception as e:
        typer.echo(f"Warning: Bundle validation failed: {e}", err=True)
        typer.echo("The bundle was created but may have issues. Check the files manually.", err=True)

    # Print next steps
    typer.echo(f"\nRBAC policy ingested: {new_env_dir}")
    typer.echo(f"Environment ID: {new_env_id}")
    typer.echo("\nRun governance assessment (customer data stays local):")
    typer.echo("  AOBENCH_SKIP_FIDELITY=1 uv run aobench run all \\")
    typer.echo("    --split dev --adapter openai:<model> --no-langfuse")
    typer.echo("\nGenerate governance report:")
    typer.echo("  uv run aobench report governance data/runs/<run_id>")
    typer.echo("\nNote: Use --no-langfuse to keep customer RBAC policy data local.")
