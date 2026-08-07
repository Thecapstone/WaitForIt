from datetime import timedelta

from django.utils import timezone
import pytest

from authentication.models import User
from inference.context import generate_article_context
from memories.models import Capsule, Logs

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(email="developer@example.com", password="password")


@pytest.fixture
def capsule(user):
    return Capsule.objects.create(
        title="WaitForIt",
        description="Developer visibility",
        creator=user,
    )


def create_log(capsule, user, title, minutes):
    log = Logs.objects.create(
        capsule=capsule,
        creator=user,
        stamp=title.lower().replace(" ", "_"),
        title=title,
        description=f"{title} details",
        code_language="Python",
        code_framework="Django",
    )
    created_at = timezone.now() + timedelta(minutes=minutes)
    Logs.objects.filter(id=log.id).update(created_at=created_at)
    log.refresh_from_db()
    return log


def test_generate_article_context_aggregates_logs(capsule, user):
    later = create_log(capsule, user, "Added refresh tokens", 30)
    earlier = create_log(capsule, user, "Implemented JWT", 0)

    context = generate_article_context([later, earlier])

    assert context.title == "WaitForIt daily development update"
    assert context.log_count == 2
    assert context.capsule == capsule
    assert context.capsule_name == "WaitForIt"
    assert context.language == "Python"
    assert context.framework == "Django"
    assert context.primary_log == earlier
    assert "Implemented JWT" in context.timeline
    assert context.timeline.index("Implemented JWT") < context.timeline.index(
        "Added refresh tokens"
    )
