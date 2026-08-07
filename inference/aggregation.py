from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time

from django.db.models import QuerySet
from django.utils import timezone

from memories.models import Capsule, Logs


@dataclass(frozen=True)
class TimelineEntry:
    timestamp: datetime
    title: str
    description: str

    @property
    def display_time(self) -> str:
        return timezone.localtime(self.timestamp).strftime("%H:%M")


@dataclass(frozen=True)
class DailyLogBatch:
    capsule: Capsule
    logs: tuple[Logs, ...]
    timeline: tuple[TimelineEntry, ...]
    languages: tuple[str, ...]
    frameworks: tuple[str, ...]
    starts_at: datetime
    ends_at: datetime

    @property
    def primary_log(self) -> Logs:
        return self.logs[0]

    @property
    def title(self) -> str:
        if len(self.logs) == 1:
            return self.logs[0].title
        return f"{self.capsule.title} daily development update"

    @property
    def formatted_timeline(self) -> str:
        return "\n\n".join(
            f"{entry.display_time}\n{entry.title}\n{entry.description}"
            for entry in self.timeline
        )


def unique_non_empty(values: Iterable[str | None]) -> tuple[str, ...]:
    seen = []

    for value in values:
        normalized = (value or "").strip()

        if normalized and normalized not in seen:
            seen.append(normalized)

    return tuple(seen)


def order_logs(logs: Iterable[Logs]) -> tuple[Logs, ...]:
    return tuple(sorted(logs, key=lambda log: log.created_at))


def build_daily_log_batch(logs: Sequence[Logs]) -> DailyLogBatch:
    ordered_logs = order_logs(logs)

    if not ordered_logs:
        raise ValueError("Cannot build an article batch without logs.")

    capsule = ordered_logs[0].capsule

    if any(log.capsule_id != capsule.id for log in ordered_logs):
        raise ValueError("All logs in an article batch must belong to one capsule.")

    timeline = tuple(
        TimelineEntry(
            timestamp=log.created_at,
            title=log.title,
            description=log.description,
        )
        for log in ordered_logs
    )

    return DailyLogBatch(
        capsule=capsule,
        logs=ordered_logs,
        timeline=timeline,
        languages=unique_non_empty(log.code_language for log in ordered_logs),
        frameworks=unique_non_empty(log.code_framework for log in ordered_logs),
        starts_at=ordered_logs[0].created_at,
        ends_at=ordered_logs[-1].created_at,
    )


def day_bounds(day: date | None = None) -> tuple[datetime, datetime]:
    target_day = day or timezone.localdate()
    current_timezone = timezone.get_current_timezone()

    starts_at = timezone.make_aware(
        datetime.combine(target_day, time.min),
        current_timezone,
    )
    ends_at = timezone.make_aware(
        datetime.combine(target_day, time.max),
        current_timezone,
    )

    return starts_at, ends_at


def logs_for_capsule_day(
    capsule_id: str,
    day: date | None = None,
) -> QuerySet[Logs]:
    starts_at, ends_at = day_bounds(day)

    return (
        Logs.objects
        .select_related("capsule", "creator")
        .filter(
            capsule_id=capsule_id,
            created_at__gte=starts_at,
            created_at__lte=ends_at,
            is_generated=False,
        )
        .order_by("created_at")
    )


def daily_batches(day: date | None = None) -> list[DailyLogBatch]:
    starts_at, ends_at = day_bounds(day)
    capsule_ids = (
        Logs.objects
        .filter(
            created_at__gte=starts_at,
            created_at__lte=ends_at,
            is_generated=False,
        )
        .order_by("capsule_id")
        .values_list("capsule_id", flat=True)
        .distinct()
    )

    batches = []

    for capsule_id in capsule_ids:
        logs = tuple(logs_for_capsule_day(capsule_id, day))

        if logs:
            batches.append(build_daily_log_batch(logs))

    return batches
