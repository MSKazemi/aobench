"""Tests for --models multi-model flag and --system-prompt-prefix RBAC plumbing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer


# ---------------------------------------------------------------------------
# resolve_model tests
# ---------------------------------------------------------------------------


def test_resolve_model_direct_qa():
    from aobench.cli.run_cmd import resolve_model
    from aobench.adapters.direct_qa_adapter import DirectQAAdapter

    adapter_class, model_name = resolve_model("direct_qa")
    assert adapter_class is DirectQAAdapter
    assert model_name == "direct_qa"


def test_resolve_model_gpt4o():
    from aobench.cli.run_cmd import resolve_model
    from aobench.adapters.openai_adapter import OpenAIAdapter

    adapter_class, model_name = resolve_model("gpt-4o")
    assert adapter_class is OpenAIAdapter
    assert model_name == "gpt-4o-2024-11-20"


def test_resolve_model_gpt4o_mini():
    from aobench.cli.run_cmd import resolve_model
    from aobench.adapters.openai_adapter import OpenAIAdapter

    adapter_class, model_name = resolve_model("gpt-4o-mini")
    assert adapter_class is OpenAIAdapter
    assert model_name == "gpt-4o-mini-2024-07-18"


def test_resolve_model_llama():
    from aobench.cli.run_cmd import resolve_model
    from aobench.adapters.openai_adapter import OpenAIAdapter

    adapter_class, model_name = resolve_model("llama-3.3-70b")
    assert adapter_class is OpenAIAdapter
    assert model_name == "meta-llama/Llama-3.3-70B-Instruct-Turbo"


def test_resolve_model_unknown_exits():
    """Unknown token must raise typer.Exit (exit code 1)."""
    from aobench.cli.run_cmd import resolve_model

    with pytest.raises(typer.Exit):
        resolve_model("totally-unknown-model-xyz")


def test_resolve_model_unknown_prints_valid_tokens(capsys):
    """Unknown token should print the list of valid tokens."""
    from aobench.cli.run_cmd import resolve_model, _MODEL_REGISTRY

    with pytest.raises(typer.Exit):
        resolve_model("totally-unknown-model-xyz")

    captured = capsys.readouterr()
    # The error message goes to stderr via typer.echo(..., err=True)
    for token in _MODEL_REGISTRY:
        assert token in captured.err


# ---------------------------------------------------------------------------
# --models routing logic: verifies subdirectory output paths
# ---------------------------------------------------------------------------


def test_run_all_models_creates_subdir_output_paths(tmp_path):
    """run all --models direct_qa,direct_qa should route to two separate token subdirs."""
    from aobench.cli.run_cmd import _MODEL_REGISTRY, resolve_model

    tokens = ["direct_qa", "direct_qa"]
    expected_dirs = [str(tmp_path / token) for token in tokens]

    # Verify the routing logic: each token maps to <output>/<token>/
    for token, expected_dir in zip(tokens, expected_dirs):
        adapter_class, model_name = resolve_model(token)
        out = str(Path(str(tmp_path)) / token)
        assert out == expected_dir


def test_models_flag_iterates_all_tokens(tmp_path):
    """Verify that each token in --models produces a separate output subdirectory path."""
    tokens = ["direct_qa", "gpt-4o", "llama-3.3-70b"]
    output_root = str(tmp_path)

    from aobench.cli.run_cmd import resolve_model

    seen_outputs = []
    for token in tokens:
        adapter_class, model_name = resolve_model(token)
        token_output = str(Path(output_root) / token)
        seen_outputs.append(token_output)

    assert len(seen_outputs) == len(tokens)
    assert len(set(seen_outputs)) == len(tokens), "Each token should map to a unique output dir"


# ---------------------------------------------------------------------------
# --system-prompt-prefix rendering
# ---------------------------------------------------------------------------


def test_load_system_prompt_prefix_substitution(tmp_path):
    """Prefix file with {{role}}, {{permitted_tools_csv}}, {{forbidden_tools_csv}} must be filled."""
    from aobench.cli.run_cmd import _load_system_prompt_prefix

    prefix_file = tmp_path / "prefix.txt"
    prefix_file.write_text(
        "Role: {{role}}\nPermitted: {{permitted_tools_csv}}\nForbidden: {{forbidden_tools_csv}}\n",
        encoding="utf-8",
    )

    task = MagicMock()
    task.role = "sysadmin"
    task.allowed_tools = ["slurm", "docs"]
    task.hard_fail_conditions = ["rbac__check"]

    result = _load_system_prompt_prefix(str(prefix_file), task)

    assert "sysadmin" in result
    assert "slurm" in result
    assert "docs" in result
    assert "rbac__check" in result
    assert "{{role}}" not in result
    assert "{{permitted_tools_csv}}" not in result
    assert "{{forbidden_tools_csv}}" not in result


def test_load_system_prompt_prefix_none_returns_empty():
    """When path is None, _load_system_prompt_prefix must return an empty string."""
    from aobench.cli.run_cmd import _load_system_prompt_prefix

    task = MagicMock()
    result = _load_system_prompt_prefix(None, task)
    assert result == ""


def test_load_system_prompt_prefix_empty_lists(tmp_path):
    """Task with no allowed_tools or hard_fail_conditions should produce empty CSV fields."""
    from aobench.cli.run_cmd import _load_system_prompt_prefix

    prefix_file = tmp_path / "prefix.txt"
    prefix_file.write_text(
        "P:{{permitted_tools_csv}} F:{{forbidden_tools_csv}}",
        encoding="utf-8",
    )

    task = MagicMock()
    task.role = "scientific_user"
    task.allowed_tools = None
    task.hard_fail_conditions = []

    result = _load_system_prompt_prefix(str(prefix_file), task)
    assert "P: F:" in result


def test_system_prompt_prefix_prepended_to_adapter_system_prompt(tmp_path):
    """Verify that the resolved prefix appears at the start of the adapter system prompt."""
    from aobench.adapters.openai_adapter import OpenAIAdapter
    from aobench.cli.run_cmd import _load_system_prompt_prefix

    prefix_file = tmp_path / "prefix.txt"
    prefix_file.write_text("RBAC PREAMBLE: role={{role}}", encoding="utf-8")

    task = MagicMock()
    task.role = "facility_admin"
    task.allowed_tools = ["facility"]
    task.hard_fail_conditions = []

    adapter = OpenAIAdapter(model="gpt-4o-2024-11-20")
    original_prompt = adapter._system_prompt

    prefix = _load_system_prompt_prefix(str(prefix_file), task)
    assert prefix  # should not be empty

    combined = prefix + "\n\n" + original_prompt
    adapter._system_prompt = combined

    assert adapter._system_prompt.startswith("RBAC PREAMBLE:")
    assert "facility_admin" in adapter._system_prompt
    assert original_prompt in adapter._system_prompt
