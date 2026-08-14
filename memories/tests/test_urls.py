from django.urls import resolve, reverse
import pytest

pytestmark = pytest.mark.django_db


def test_create_log_route_resolves_to_action():
    match = resolve("/api/memories/abc123/create-log/")

    assert match.url_name == "memories-create-log"
    assert match.kwargs == {"pk": "abc123"}


def test_create_log_route_is_reversible():
    url = reverse(
        "api:memories-create-log",
        kwargs={"pk": "abc123"},
    )

    assert url == "/api/memories/abc123/create-log/"


def test_log_read_route_resolves():
    match = resolve("/api/memories/abc123/log/")

    assert match.url_name == "memories-retrieve-log"
