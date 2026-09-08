from pathlib import Path

import yaml

PROMPT_FILE = Path(__file__).resolve().parents[1] / "prompt" / "prompts.yml"


def test_prompt_file_exists_and_parses():
    data = yaml.safe_load(PROMPT_FILE.read_text(encoding="utf-8"))
    assert "main_agent" in data
    assert "sub_agents" in data


def test_main_agent_prompt_complete():
    data = yaml.safe_load(PROMPT_FILE.read_text(encoding="utf-8"))
    prompt = data["main_agent"]["system_prompt"]
    assert len(prompt) > 200
    assert "子智能体" in prompt or "助手" in prompt


def test_sub_agents_complete():
    data = yaml.safe_load(PROMPT_FILE.read_text(encoding="utf-8"))
    for key in ("tavily", "db", "ragflow"):
        sub = data["sub_agents"][key]
        assert all(k in sub for k in ("name", "description", "system_prompt")), key


def test_agent_prompts_module_loads():
    import agent.prompts  # noqa: F401

    assert agent.prompts.main_agent_content["system_prompt"]