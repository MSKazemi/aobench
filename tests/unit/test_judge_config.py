"""Unit tests for exabench.judge.config."""

from __future__ import annotations

import pytest

from exabench.judge.config import JudgeConfig, make_judge_config_id


RUBRIC_TEXT = "# Rubric prompt\nSystem: score the response."
TAXONOMY_TEXT = "# Taxonomy prompt\nSystem: annotate errors."


class TestJudgeConfigDefaults:
    def test_default_model(self):
        cfg = JudgeConfig()
        assert cfg.model == "gpt-4o-2024-11-20"

    def test_default_temperature(self):
        cfg = JudgeConfig()
        assert cfg.temperature == 0.0

    def test_default_top_p(self):
        cfg = JudgeConfig()
        assert cfg.top_p == 1.0

    def test_default_max_tokens_rubric(self):
        cfg = JudgeConfig()
        assert cfg.max_tokens_rubric == 1024

    def test_default_max_tokens_taxonomy(self):
        cfg = JudgeConfig()
        assert cfg.max_tokens_taxonomy == 256

    def test_default_seed_offset(self):
        cfg = JudgeConfig()
        assert cfg.seed_offset == 0


class TestMakeJudgeConfigId:
    def test_returns_16_hex_chars(self):
        cfg = JudgeConfig()
        cid = make_judge_config_id(cfg, RUBRIC_TEXT, TAXONOMY_TEXT)
        assert isinstance(cid, str)
        assert len(cid) == 16
        assert all(c in "0123456789abcdef" for c in cid)

    def test_deterministic_same_inputs(self):
        cfg = JudgeConfig()
        cid1 = make_judge_config_id(cfg, RUBRIC_TEXT, TAXONOMY_TEXT)
        cid2 = make_judge_config_id(cfg, RUBRIC_TEXT, TAXONOMY_TEXT)
        assert cid1 == cid2

    def test_changes_when_model_changes(self):
        cfg_a = JudgeConfig(model="gpt-4o-2024-11-20")
        cfg_b = JudgeConfig(model="gpt-4o-mini-2024-07-18")
        cid_a = make_judge_config_id(cfg_a, RUBRIC_TEXT, TAXONOMY_TEXT)
        cid_b = make_judge_config_id(cfg_b, RUBRIC_TEXT, TAXONOMY_TEXT)
        assert cid_a != cid_b

    def test_changes_when_temperature_changes(self):
        cfg_a = JudgeConfig(temperature=0.0)
        cfg_b = JudgeConfig(temperature=0.5)
        cid_a = make_judge_config_id(cfg_a, RUBRIC_TEXT, TAXONOMY_TEXT)
        cid_b = make_judge_config_id(cfg_b, RUBRIC_TEXT, TAXONOMY_TEXT)
        assert cid_a != cid_b

    def test_changes_when_top_p_changes(self):
        cfg_a = JudgeConfig(top_p=1.0)
        cfg_b = JudgeConfig(top_p=0.9)
        cid_a = make_judge_config_id(cfg_a, RUBRIC_TEXT, TAXONOMY_TEXT)
        cid_b = make_judge_config_id(cfg_b, RUBRIC_TEXT, TAXONOMY_TEXT)
        assert cid_a != cid_b

    def test_changes_when_max_tokens_rubric_changes(self):
        cfg_a = JudgeConfig(max_tokens_rubric=1024)
        cfg_b = JudgeConfig(max_tokens_rubric=512)
        cid_a = make_judge_config_id(cfg_a, RUBRIC_TEXT, TAXONOMY_TEXT)
        cid_b = make_judge_config_id(cfg_b, RUBRIC_TEXT, TAXONOMY_TEXT)
        assert cid_a != cid_b

    def test_changes_when_max_tokens_taxonomy_changes(self):
        cfg_a = JudgeConfig(max_tokens_taxonomy=256)
        cfg_b = JudgeConfig(max_tokens_taxonomy=128)
        cid_a = make_judge_config_id(cfg_a, RUBRIC_TEXT, TAXONOMY_TEXT)
        cid_b = make_judge_config_id(cfg_b, RUBRIC_TEXT, TAXONOMY_TEXT)
        assert cid_a != cid_b

    def test_changes_when_rubric_text_changes(self):
        cfg = JudgeConfig()
        cid_a = make_judge_config_id(cfg, RUBRIC_TEXT, TAXONOMY_TEXT)
        cid_b = make_judge_config_id(cfg, RUBRIC_TEXT + " extra", TAXONOMY_TEXT)
        assert cid_a != cid_b

    def test_changes_when_taxonomy_text_changes(self):
        cfg = JudgeConfig()
        cid_a = make_judge_config_id(cfg, RUBRIC_TEXT, TAXONOMY_TEXT)
        cid_b = make_judge_config_id(cfg, RUBRIC_TEXT, TAXONOMY_TEXT + " extra")
        assert cid_a != cid_b

    def test_seed_offset_does_not_affect_config_id(self):
        """seed_offset is per-task, not part of judge config identity."""
        cfg_a = JudgeConfig(seed_offset=0)
        cfg_b = JudgeConfig(seed_offset=42)
        cid_a = make_judge_config_id(cfg_a, RUBRIC_TEXT, TAXONOMY_TEXT)
        cid_b = make_judge_config_id(cfg_b, RUBRIC_TEXT, TAXONOMY_TEXT)
        assert cid_a == cid_b

    def test_different_configs_produce_different_ids(self):
        """Smoke test: several distinct configs all yield distinct IDs."""
        configs = [
            JudgeConfig(model="gpt-4o-2024-11-20"),
            JudgeConfig(model="gpt-4o-mini-2024-07-18"),
            JudgeConfig(temperature=0.3),
            JudgeConfig(max_tokens_rubric=2048),
        ]
        ids = [make_judge_config_id(c, RUBRIC_TEXT, TAXONOMY_TEXT) for c in configs]
        assert len(set(ids)) == len(ids), "All configs should yield unique IDs"
