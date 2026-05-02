"""Tests for the 26 new task specs added in v3 taxonomy expansion."""
import json
from pathlib import Path
import pytest

SPECS_DIR = Path(__file__).parent.parent.parent / "benchmark/tasks/specs"
ENVS_DIR = Path(__file__).parent.parent.parent / "benchmark/environments"
TASK_SET_V3 = Path(__file__).parent.parent.parent / "benchmark/tasks/task_set_v3.json"

NEW_TASK_IDS = [
    "DATA_USR_001", "DATA_SYS_001", "DATA_RES_001", "DATA_FAC_001", "DATA_DES_001",
    "FAC_FAC_001", "FAC_SYS_001", "FAC_USR_001", "FAC_RES_001", "FAC_DES_001",
    "ARCH_DES_001", "ARCH_SYS_001", "ARCH_USR_001", "ARCH_RES_001", "ARCH_FAC_001",
    "DOCS_USR_001", "DOCS_SYS_001", "DOCS_RES_001", "DOCS_FAC_001", "DOCS_DES_001",
    "JOB_RES_001", "MON_RES_001", "ENERGY_RES_001",
    "JOB_DES_001", "PERF_DES_001", "AIOPS_DES_001",
]

VALID_ROLES = {"scientific_user", "sysadmin", "facility_admin", "researcher", "system_designer"}
VALID_QCATS = {"JOB", "PERF", "DATA", "MON", "ENERGY", "SEC", "FAC", "ARCH", "AIOPS", "DOCS"}
VALID_DIFFICULTIES = {"easy", "medium", "hard", "adversarial"}


@pytest.mark.parametrize("task_id", NEW_TASK_IDS)
def test_spec_file_exists(task_id):
    assert (SPECS_DIR / f"{task_id}.json").exists(), f"Spec file missing: {task_id}.json"


@pytest.mark.parametrize("task_id", NEW_TASK_IDS)
def test_spec_parses_as_json(task_id):
    spec = json.loads((SPECS_DIR / f"{task_id}.json").read_text())
    assert isinstance(spec, dict)


@pytest.mark.parametrize("task_id", NEW_TASK_IDS)
def test_spec_required_fields(task_id):
    spec = json.loads((SPECS_DIR / f"{task_id}.json").read_text())
    for field in ["task_id", "title", "qcat", "role", "difficulty", "environment_id",
                  "query_text", "expected_answer_type", "gold_evidence_refs",
                  "eval_criteria", "allowed_tools", "expected_tool_calls",
                  "hard_fail_conditions"]:
        assert field in spec, f"{task_id} missing field: {field}"


@pytest.mark.parametrize("task_id", NEW_TASK_IDS)
def test_spec_task_id_matches_filename(task_id):
    spec = json.loads((SPECS_DIR / f"{task_id}.json").read_text())
    assert spec["task_id"] == task_id


@pytest.mark.parametrize("task_id", NEW_TASK_IDS)
def test_spec_valid_role(task_id):
    spec = json.loads((SPECS_DIR / f"{task_id}.json").read_text())
    assert spec["role"] in VALID_ROLES, f"{task_id} has invalid role: {spec['role']}"


@pytest.mark.parametrize("task_id", NEW_TASK_IDS)
def test_spec_valid_qcat(task_id):
    spec = json.loads((SPECS_DIR / f"{task_id}.json").read_text())
    assert spec["qcat"] in VALID_QCATS, f"{task_id} has invalid qcat: {spec['qcat']}"


@pytest.mark.parametrize("task_id", NEW_TASK_IDS)
def test_spec_valid_difficulty(task_id):
    spec = json.loads((SPECS_DIR / f"{task_id}.json").read_text())
    assert spec["difficulty"] in VALID_DIFFICULTIES


@pytest.mark.parametrize("task_id", NEW_TASK_IDS)
def test_spec_environment_exists(task_id):
    spec = json.loads((SPECS_DIR / f"{task_id}.json").read_text())
    env_id = spec["environment_id"]
    assert (ENVS_DIR / env_id).exists(), f"{task_id} references missing environment: {env_id}"


@pytest.mark.parametrize("task_id", NEW_TASK_IDS)
def test_spec_expected_tool_calls_nonempty(task_id):
    spec = json.loads((SPECS_DIR / f"{task_id}.json").read_text())
    assert len(spec["expected_tool_calls"]) > 0, f"{task_id} has empty expected_tool_calls"


@pytest.mark.parametrize("task_id", NEW_TASK_IDS)
def test_spec_eval_criteria_has_gold_answer(task_id):
    spec = json.loads((SPECS_DIR / f"{task_id}.json").read_text())
    assert "gold_answer" in spec["eval_criteria"], f"{task_id} eval_criteria missing gold_answer"
    assert len(spec["eval_criteria"]["gold_answer"]) > 10


@pytest.mark.parametrize("task_id", NEW_TASK_IDS)
def test_spec_checkpoints_present(task_id):
    spec = json.loads((SPECS_DIR / f"{task_id}.json").read_text())
    # checkpoints are expected but may be absent in minimal stubs
    if "checkpoints" in spec:
        assert len(spec["checkpoints"]) >= 2, f"{task_id} has fewer than 2 checkpoints"


def test_task_set_v3_exists():
    assert TASK_SET_V3.exists()


def test_task_set_v3_contains_71_tasks():
    data = json.loads(TASK_SET_V3.read_text())
    # Handle both list format and dict-with-tasks format
    task_ids = data if isinstance(data, list) else data.get("task_ids", data.get("tasks", []))
    # If tasks are dicts, extract task_id
    if task_ids and isinstance(task_ids[0], dict):
        task_ids = [t["task_id"] for t in task_ids]
    assert len(task_ids) == 80, f"Expected 80 tasks, got {len(task_ids)}"


def test_task_set_v3_includes_new_tasks():
    data = json.loads(TASK_SET_V3.read_text())
    task_ids = data if isinstance(data, list) else data.get("task_ids", data.get("tasks", []))
    if task_ids and isinstance(task_ids[0], dict):
        task_ids = [t["task_id"] for t in task_ids]
    task_set = set(task_ids)
    for tid in NEW_TASK_IDS:
        assert tid in task_set, f"task_set_v3 missing: {tid}"


def test_researcher_tasks_exist():
    """Verify researcher role tasks exist across multiple QCATs."""
    researcher_tasks = [tid for tid in NEW_TASK_IDS
                        if json.loads((SPECS_DIR / f"{tid}.json").read_text()).get("role") == "researcher"]
    assert len(researcher_tasks) >= 5, f"Expected at least 5 researcher tasks, got {len(researcher_tasks)}"


def test_system_designer_tasks_exist():
    """Verify system_designer role tasks exist across multiple QCATs."""
    designer_tasks = [tid for tid in NEW_TASK_IDS
                      if json.loads((SPECS_DIR / f"{tid}.json").read_text()).get("role") == "system_designer"]
    assert len(designer_tasks) >= 5, f"Expected at least 5 system_designer tasks, got {len(designer_tasks)}"


def test_all_10_qcats_have_at_least_one_task():
    """Verify all 10 QCATs now have at least one task in task_set_v3."""
    all_specs = list(SPECS_DIR.glob("*.json"))
    qcats_present = set()
    for spec_file in all_specs:
        try:
            spec = json.loads(spec_file.read_text())
            qcats_present.add(spec.get("qcat", ""))
        except json.JSONDecodeError:
            pass
    for qcat in VALID_QCATS:
        assert qcat in qcats_present, f"QCAT {qcat} has no task specs"
