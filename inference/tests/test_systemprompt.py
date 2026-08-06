from inference.systemPrompt import system_prompt


def test_system_prompt_contains_previous_work():
    prompt = system_prompt("My previous article")

    assert "My previous article" in prompt
    assert "ARTICLE STRUCTURE" in prompt
