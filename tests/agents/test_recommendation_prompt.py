from tests.agents.collectors.import_helpers import load_module, recommendation_agent_path


def test_prompt_includes_scada_and_strict_json():
    module = load_module("prompt_builder", recommendation_agent_path("prompt_builder.py"))

    prompt = module.build_prompt({"scada_tag_health": [{"source_id": "tag1", "quality": "bad"}]})

    assert "scada_tag_health" in prompt
    assert "JSON estricto" in prompt
    assert "tag1" in prompt
