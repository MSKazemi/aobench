#!/usr/bin/env python3
"""One-shot: serialise the canonical v0.2 JudgeConfig to data/judge_config.json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from aobench.judge.config import JudgeConfig, make_judge_config_id

RUBRIC_PATH = Path("prompts/judge/rubric_v2.md")
TAXONOMY_PATH = Path("prompts/judge/taxonomy_v2.md")
OUTPUT = Path("data/judge_config.json")

def main() -> None:
    config = JudgeConfig(
        model="gpt-4o-2024-11-20",
        temperature=0.0,
    )
    rubric_text = RUBRIC_PATH.read_text()
    taxonomy_text = TAXONOMY_PATH.read_text()
    config_id = make_judge_config_id(config, rubric_text, taxonomy_text)

    payload = {
        "judge_config_id": config_id,
        "model": config.model,
        "temperature": config.temperature,
        "top_p": config.top_p,
        "max_tokens_rubric": config.max_tokens_rubric,
        "max_tokens_taxonomy": config.max_tokens_taxonomy,
        "seed_offset": config.seed_offset,
        "rubric_path": str(RUBRIC_PATH),
        "taxonomy_path": str(TAXONOMY_PATH),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"judge_config_id: {config_id}")
    print(f"Written to: {OUTPUT}")

if __name__ == "__main__":
    main()
