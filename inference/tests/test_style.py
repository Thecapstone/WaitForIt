from inference.style import writing_style


def test_writing_style_without_sample():
    prompt = writing_style()

    assert "AUTHOR WRITING PROFILE" in prompt
    assert "No previous writing samples" in prompt
