# ruff: noqa: F403,F405

from .settings import *


class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


USE_REAL_DATABASE_FOR_TESTS = env.bool("USE_REAL_DATABASE_FOR_TESTS", default=False)

if not USE_REAL_DATABASE_FOR_TESTS:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            "TEST": {
                "NAME": BASE_DIR / ".pytest.sqlite3",
            },
            "CONN_MAX_AGE": 0,
            "CONN_HEALTH_CHECKS": False,
            "OPTIONS": {
                "timeout": 20,
            },
        }
    }

MIGRATION_MODULES = DisableMigrations()

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
