from textwrap import dedent

from .context import ArticleContext


class PromptBuilder:
    """
    Builds task-specific user prompts.

    The system prompt is responsible for tone and writing style.

    This class only describes today's task.
    """

    @staticmethod
    def article(context: ArticleContext) -> str:
        return dedent(
            f"""
            Generate a technical blog article using the information below.

            ## Article Information

            Title:
            {context.title}

            Project:
            {context.capsule_name}

            Programming Language:
            {context.language}

            Framework:
            {context.framework}

            Development Session:
            {context.starts_at:%Y-%m-%d %H:%M} - {context.ends_at:%H:%M}

            Log Count:
            {context.log_count}

            Capsule Metadata:
            {context.capsule_metadata or "Not specified"}

            Development Timeline:

            {context.timeline}

            Requirements:

            - Use the complete development timeline to write one cohesive article.
            - Do not invent implementation details.
            - Explain the motivation behind decisions.
            - Explain challenges where appropriate.
            - Maintain a logical flow.
            - Keep technical explanations accessible.
            - Produce a publishable article.

            Return only the article.
            """
        ).strip()

    @staticmethod
    def summary(article: str) -> str:
        return dedent(
            f"""
            Produce a concise summary of the article below.

            Requirements:

            - Maximum 100 words.
            - Begin with "TL;DR:"
            - Capture the key lessons.
            - Use bullet points only if they improve clarity.

            Article:

            {article}
            """
        ).strip()

    @staticmethod
    def tags(article: str) -> str:
        return dedent(
            f"""
            Generate between 3 and 7 technical tags for the article below.

            Return ONLY a JSON array of strings.

            Article:

            {article}
            """
        ).strip()

    @staticmethod
    def title(article: str) -> str:
        return dedent(
            f"""
            Generate a concise, engaging title for the article below.

            The title should:

            - Be technically accurate.
            - Spark curiosity.
            - Avoid clickbait.
            - Be under 70 characters.

            Return only the title.

            Article:

            {article}
            """
        ).strip()
