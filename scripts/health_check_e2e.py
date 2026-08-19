"""End-to-end health check for the Wait-For-It API.

The script logs in, creates a capsule, creates several logs, and polls until an
article appears on the capsule view.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
import sys
import time
from typing import Any
from uuid import uuid4

import requests

DEFAULT_EMAIL = "visionariesnails@gmail.com"
DEFAULT_PASSWORD = "testpassword"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_POLL_INTERVAL_SECONDS = 10
PROJECT_ROOT = Path(__file__).resolve().parents[1]


class HealthCheckError(Exception):
    """Raised when an e2e health check step fails."""


@dataclass(frozen=True)
class HealthCheckConfig:
    base_url: str
    email: str
    password: str
    log_count: int
    timeout_seconds: int
    poll_interval_seconds: int
    generate_now: bool


def api_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def require_success(response: requests.Response, step: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text[:1000]}

    if not response.ok:
        raise HealthCheckError(
            f"{step} failed with HTTP {response.status_code}: {payload}"
        )

    return payload


def login(session: requests.Session, config: HealthCheckConfig) -> None:
    response = session.post(
        api_url(config.base_url, "/api/auth/login/"),
        json={"email": config.email, "password": config.password},
        timeout=30,
    )
    require_success(response, "login")

    access_token = response.cookies.get("access_token")
    if not access_token:
        raise HealthCheckError("login succeeded, but no access_token cookie was set")

    # Login cookies are marked Secure. For local HTTP health checks, requests will
    # store them but not send them back, so use the same token as a bearer token.
    session.headers.update({"Authorization": f"Bearer {access_token}"})


def create_capsule(session: requests.Session, config: HealthCheckConfig) -> str:
    run_id = datetime.now(tz=UTC).strftime("%Y%m%d%H%M%S")
    title = f"health-check-capsule-{run_id}-{uuid4().hex[:8]}"
    maturity_date = (datetime.now(tz=UTC) + timedelta(days=1)).isoformat()

    response = session.post(
        api_url(config.base_url, "/api/memories/create/"),
        json={
            "title": title,
            "description": "Automated e2e health check capsule.",
            "maturity_date": maturity_date,
            "private": True,
        },
        headers={"Idempotency-Key": f"health-capsule-{uuid4()}"},
        timeout=300,
    )
    payload = require_success(response, "create capsule")

    capsule_id = payload.get("id")
    if not capsule_id:
        raise HealthCheckError(f"create capsule returned no id: {payload}")

    print(f"created capsule: {capsule_id} ({title})")
    return str(capsule_id)


def create_logs(
    session: requests.Session,
    config: HealthCheckConfig,
    capsule_id: str,
) -> None:
    samples = [
        (
            "Authentication wiring",
            "Validated login, cookie JWT behavior, and session state for the health check run.",
        ),
        (
            "Capsule workflow",
            "Created a new capsule and confirmed the API accepts future maturity dates.",
        ),
        (
            "Generation input",
            "Added multiple development logs so the article generation pipeline has context.",
        ),
    ]

    for index in range(config.log_count):
        title, description = samples[index % len(samples)]
        response = session.post(
            api_url(config.base_url, f"/api/memories/{capsule_id}/create-log/"),
            json={
                "title": f"{title} #{index + 1}",
                "description": description,
                "code_language": "Python",
                "code_framework": "Django REST Framework",
            },
            headers={"Idempotency-Key": f"health-log-{capsule_id}-{index}-{uuid4()}"},
            timeout=300,
        )
        require_success(response, f"create log {index + 1}")
        print(f"created log {index + 1}/{config.log_count}")


def trigger_generation_locally(capsule_id: str) -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, str(PROJECT_ROOT))

    import django

    django.setup()

    from inference.tasks import generate_daily_article_for_capsule

    article_id = generate_daily_article_for_capsule(str(capsule_id))
    if not article_id:
        raise HealthCheckError("local generation ran, but did not return an article id")
    print(f"triggered local article generation: {article_id}")


def articles_from_capsule_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    capsule_data = payload.get("data", payload)
    articles = capsule_data.get("articles") if isinstance(capsule_data, dict) else None
    if not isinstance(articles, list):
        return []
    return [article for article in articles if isinstance(article, dict)]


def wait_for_article(
    session: requests.Session,
    config: HealthCheckConfig,
    capsule_id: str,
) -> dict[str, Any]:
    deadline = time.monotonic() + config.timeout_seconds
    attempt = 0

    while time.monotonic() < deadline:
        attempt += 1
        response = session.get(
            api_url(config.base_url, f"/api/memories/{capsule_id}/view/"),
            timeout=300,
        )
        payload = require_success(response, "view capsule")
        articles = articles_from_capsule_payload(payload)

        if articles:
            article = articles[-1]
            if article.get("id") and article.get("body"):
                return article

        print(
            "article not ready yet "
            f"(attempt {attempt}, waiting {config.poll_interval_seconds}s)"
        )
        time.sleep(config.poll_interval_seconds)

    raise HealthCheckError(
        f"timed out after {config.timeout_seconds}s waiting for an article"
    )


def parse_args() -> HealthCheckConfig:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.getenv("WFI_BASE_URL", DEFAULT_BASE_URL),
        help=f"API base URL. Defaults to {DEFAULT_BASE_URL}.",
    )
    parser.add_argument(
        "--email",
        default=os.getenv("WFI_HEALTH_EMAIL", DEFAULT_EMAIL),
        help="Login email. Can also be set with WFI_HEALTH_EMAIL.",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("WFI_HEALTH_PASSWORD", DEFAULT_PASSWORD),
        help="Login password. Can also be set with WFI_HEALTH_PASSWORD.",
    )
    parser.add_argument(
        "--log-count",
        type=int,
        default=int(os.getenv("WFI_HEALTH_LOG_COUNT", "3")),
        help="Number of logs to create under the capsule.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=int(os.getenv("WFI_HEALTH_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)),
        help="Maximum time to wait for article generation.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=int(
            os.getenv(
                "WFI_HEALTH_POLL_INTERVAL_SECONDS",
                DEFAULT_POLL_INTERVAL_SECONDS,
            )
        ),
        help="Delay between capsule polling attempts.",
    )
    parser.add_argument(
        "--generate-now",
        action="store_true",
        help=(
            "Local/dev helper: after creating logs, call the Django article "
            "generation task synchronously before polling."
        ),
    )
    args = parser.parse_args()

    if args.log_count < 1:
        parser.error("--log-count must be at least 1")
    if args.timeout_seconds < 1:
        parser.error("--timeout-seconds must be at least 1")
    if args.poll_interval_seconds < 1:
        parser.error("--poll-interval-seconds must be at least 1")

    return HealthCheckConfig(
        base_url=args.base_url,
        email=args.email,
        password=args.password,
        log_count=args.log_count,
        timeout_seconds=args.timeout_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
        generate_now=args.generate_now,
    )


def main() -> int:
    config = parse_args()
    session = requests.Session()

    try:
        print(f"checking API at {config.base_url}")
        login(session, config)
        print("logged in")
        capsule_id = create_capsule(session, config)
        create_logs(session, config, capsule_id)

        if config.generate_now:
            trigger_generation_locally(capsule_id)

        article = wait_for_article(session, config, capsule_id)
    except HealthCheckError as exc:
        print(f"health check failed: {exc}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"health check failed during HTTP request: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"health check failed during local generation: {exc}", file=sys.stderr)
        return 1

    print(f"health check passed: article {article['id']} generated")
    print(f"article title: {article.get('title', '<untitled>')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
