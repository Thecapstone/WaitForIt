from datetime import timedelta

from django.utils import timezone
import pytest

from authentication.models import User
from inference.aggregation import build_daily_log_batch, daily_batches
from memories.models import Capsule, Logs

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(email="developer@example.com", password="password")


@pytest.fixture
def capsule(user):
    return Capsule.objects.create(title="WaitForIt", creator=user)


def create_log(capsule, user, title, minutes=0, is_generated=False):
    log = Logs.objects.create(
        capsule=capsule,
        creator=user,
        stamp=title,
        title=title,
        description=f"{title} details",
        code_language="Python",
        code_framework="Django",
        is_generated=is_generated,
    )
    Logs.objects.filter(id=log.id).update(
        created_at=timezone.now() + timedelta(minutes=minutes)
    )
    log.refresh_from_db()
    return log


def test_build_daily_log_batch_sorts_chronologically(capsule, user):
    later = create_log(capsule, user, "Second", 10)
    earlier = create_log(capsule, user, "First", 0)

    batch = build_daily_log_batch([later, earlier])

    assert batch.logs == (earlier, later)
    assert batch.languages == ("Python",)
    assert batch.frameworks == ("Django",)
    assert "First" in batch.formatted_timeline


def test_daily_batches_ignores_generated_logs(capsule, user):
    create_log(capsule, user, "Unused")
    create_log(capsule, user, "Already used", is_generated=True)

    batches = daily_batches()

    assert len(batches) == 1
    assert len(batches[0].logs) == 1
    assert batches[0].logs[0].title == "Unused"
