from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from memories.models import Capsule, Logs

from .aggregation import DailyLogBatch, build_daily_log_batch


@dataclass
class ArticleContext:
    title: str
    timeline: str
    log_count: int
    starts_at: datetime
    ends_at: datetime
    capsule: Capsule
    capsule_name: str
    language: str
    framework: str
    project_metadata: str
    capsule_metadata: str
    previous_articles: str | None
    primary_log: Logs
    logs: tuple[Logs, ...]


def _resolve_logs(logs: Sequence[Logs] | Sequence[str]) -> tuple[Logs, ...]:
    if not logs:
        raise ValueError("At least one log is required to generate article context.")

    if isinstance(logs[0], Logs):
        return tuple(logs)

    log_ids = [str(log_id) for log_id in logs]
    logs_by_id = {
        str(log.id): log
        for log in Logs.objects.select_related("capsule", "creator").filter(
            id__in=log_ids
        )
    }

    return tuple(logs_by_id[log_id] for log_id in log_ids if log_id in logs_by_id)


def generate_article_context(logs: Sequence[Logs] | Sequence[str]) -> ArticleContext:
    resolved_logs = _resolve_logs(logs)

    if not resolved_logs:
        raise ValueError("No matching logs were found for article generation.")

    batch: DailyLogBatch = build_daily_log_batch(resolved_logs)
    capsule = batch.capsule
    language = ", ".join(batch.languages) if batch.languages else "Not specified"
    framework = ", ".join(batch.frameworks) if batch.frameworks else "Not specified"

    return ArticleContext(
        title=batch.title,
        timeline=batch.formatted_timeline,
        log_count=len(batch.logs),
        starts_at=batch.starts_at,
        ends_at=batch.ends_at,
        capsule=capsule,
        capsule_name=capsule.title,
        language=language,
        framework=framework,
        project_metadata=f"Project: {capsule.title}",
        capsule_metadata=(capsule.description or "").strip(),
        previous_articles=capsule.previous_article,
        primary_log=batch.primary_log,
        logs=batch.logs,
    )
