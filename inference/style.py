from textwrap import dedent

DEFAULT_STYLE_PROFILE = {
    "voice": "Conversational, reflective, technically competent",
    "opening_style": "Begins with the pain point before the solution",
    "paragraph_length": "Medium-length conversational paragraphs",
    "perspective": "First person",
    "technical_depth": "Progressively increases throughout the article",
    "humor": "Sparse and understated",
    "transition_style": (
        "Natural conversational bridges such as "
        "'Now...', 'Mind you...', 'The interesting part was...'"
    ),
    "ending_style": "Reflective with practical encouragement",
    "primary_focus": "Decision-making over implementation details",
}


def writing_style(previous_work: str | None = None) -> str:
    """
    Build the author's writing DNA.

    The model should learn the author's style, never copy it.
    """

    style_summary = "\n".join(
        f"- {key.replace('_', ' ').title()}: {value}"
        for key, value in DEFAULT_STYLE_PROFILE.items()
    )

    previous_article_section = (
        previous_work.strip()
        if previous_work
        else "No previous writing samples were supplied."
    )

    return dedent(
        f"""
        ## AUTHOR WRITING PROFILE

        Use the following writing profile as the author's default voice.

        {style_summary}

        ------------------------------------------------------------

        ## AUTHOR WRITING SAMPLE

        {previous_article_section}

        ------------------------------------------------------------

        Instructions:

        Study both the writing profile and the writing sample.

        Infer the author's:

        - pacing
        - sentence rhythm
        - vocabulary
        - storytelling structure
        - paragraph length
        - transitions
        - personality
        - confidence
        - emotional progression
        - technical depth
        - preferred analogies
        - introduction style
        - conclusion style

        Never copy wording.

        Never reuse sentences.

        Never imitate phrases verbatim.

        Instead reproduce the author's writing style while producing
        completely original content.
        """
    ).strip()
