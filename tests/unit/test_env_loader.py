"""Unit tests for environment loader."""

from exabench.loaders.env_loader import load_environment
from exabench.schemas.environment import EnvironmentBundle


def test_load_environment(test_env_dir):
    bundle = load_environment(test_env_dir)
    assert isinstance(bundle, EnvironmentBundle)
    assert bundle.metadata.environment_id == "test_env_01"
    assert bundle.root_path == str(test_env_dir.resolve())


def test_load_environment_not_found(tmp_path):
    import pytest
    with pytest.raises(NotADirectoryError):
        load_environment(tmp_path / "nonexistent_env")
