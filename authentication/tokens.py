"""Custom JWT authentication backend handling cookie-based tokens."""

import datetime
import hashlib
from secrets import compare_digest
from uuid import uuid4

from django.conf import settings
from django.utils import timezone
from ipware import get_client_ip
import jwt
from rest_framework import permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from user_agents.parsers import parse

from authentication.models import (
    EmailVerificationToken,
    PasswordResetToken,
    User as user_db,
)

ACCESS_SECRET = settings.ACCESS_SECRET
SESSION_SECRET = settings.SESSION_SECRET
EMAIL_SECRET_KEY = settings.EMAIL_SECRET_KEY
ADMIN_BOOTSTRAP_TOKEN = settings.ADMIN_KEY

TokenTypes = {"EMAIL": "email_verification", "PASSWORD": "password_reset"}
ALGORITHM = "HS256"


# pylint: disable=too-few-public-methods
class CookieJWTAuthentication(JWTAuthentication):
    """Authentication class that extracts the JWT token from HTTP-only cookies."""

    def authenticate(self, request):
        """Extract access token from cookies, falling back to headers."""
        token = request.COOKIES.get("access_token")

        if not token:
            return super().authenticate(request)
        try:
            validated_token = self.get_validated_token(token)
        except AuthenticationFailed as e:
            raise AuthenticationFailed(f"Token validation failed:{e!s}") from e
        try:
            user = self.get_user(validated_token)
            return user, validated_token
        except AuthenticationFailed as e:
            raise AuthenticationFailed(f"Error retrieving user: {e!s}") from e


def create_user_agent(u_agent: str, ip: str, fingerprint: str) -> str:
    """Generate a stable, hashed device fingerprint from IP and User Agent."""
    ip_addr = ".".join(ip.split(".")[:2])
    user_agent = parse(u_agent)
    stable_string = f"{user_agent.os.family}--{user_agent.browser.family}--{user_agent.is_mobile}--{ip_addr}--{fingerprint}"

    return hashlib.sha256(stable_string.encode("utf-8")).hexdigest()


class HasBootstrapToken(permissions.BasePermission):
    """Allows access only if the client provides the correct secret master key."""

    def is_allowed(self, request, view):
        # Fetch the secret token from the server environment
        secret_key = ADMIN_BOOTSTRAP_TOKEN
        if not secret_key:
            return False  # Secure by default if env variable is missing

        # Check for matching HTTP Header (e.g., 'X-Bootstrap-Token: my-secret-key')
        client_token = request.headers.get("X-Bootstrap-Token")
        return compare_digest(client_token or "", secret_key or "")


def session_token(user_id: int, role: str, session_version: int, request) -> str:
    """Build and hash a tracking payload tracking user session versions."""
    ip_address, _ = get_client_ip(request)
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    fingerprint = hashlib.sha256(uuid4().bytes).hexdigest()
    active_devices = create_user_agent(user_agent, ip_address, fingerprint)
    payload = {
        "user_id": user_id,
        "role": role,
        "session_version": session_version + 1,
        "active_devices": active_devices,
    }
    # return hashlib.sha256(str(payload).encode("utf-8")).hexdigest()
    return jwt.encode({"payload": payload}, SESSION_SECRET, algorithm=ALGORITHM)


def access_token(session_token: str) -> str:
    """Decodes a valid session token and generates a short-lived access token."""
    try:
        # 1. Decode and verify the session token
        decoded_session = jwt.decode(
            session_token, SESSION_SECRET, algorithms=[ALGORITHM]
        )
        session_payload = decoded_session.get("payload", {})

        # 2. Extract necessary user identifiers
        user_id = session_payload.get("user_id")
        session_version = session_payload.get("session_version")
        role = session_payload.get("role")

        if not user_id or not role:
            raise ValueError("Invalid session token payload data.")

        if session_version != user_id.session_version:
            raise AuthenticationFailed("Token has been revoked.")

        # 3. Define access token payload with expiration (e.g., 15 minutes)
        access_payload = {
            "user_id": user_id,
            "role": role,
            "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=15),
            "iat": datetime.datetime.now(datetime.UTC),
            "type": "access",
        }

        # 4. Sign and return the new access token
        return jwt.encode(access_payload, ACCESS_SECRET, algorithm=ALGORITHM)

    except jwt.ExpiredSignatureError as err:
        raise ValueError("Session token has expired. Please log in again.") from err
    except jwt.InvalidTokenError as err:
        raise ValueError("Invalid session token.") from err


def generate_token(user_id, exp, token_type) -> str:
    """Generate a unique token for email verification and password reset."""
    jti = str(uuid4())

    EmailVerificationToken.objects.create(
        user=user_id,
        jti=jti,
        expires_at=exp,
    )

    payload = {
        "user_id": str(user_id),
        "type": token_type,
        "jti": jti,
        "exp": exp,
    }
    return jwt.encode(payload, EMAIL_SECRET_KEY, algorithm=ALGORITHM)


def verify_verification_token(token) -> str:
    """Verify user account using email token"""
    try:
        payload = jwt.decode(token, EMAIL_SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "email_verification":
            raise ValueError("Invalid token type.")
        return payload
    except jwt.ExpiredSignatureError as err:
        raise ValueError("Token has expired.") from err
    except jwt.InvalidTokenError as err:
        raise ValueError("Invalid token.") from err


def generate_password_reset_token(user_id, exp, token_type) -> str:
    """Generate and persist a one-time password reset token."""

    jti = uuid4()

    PasswordResetToken.objects.create(
        user=user_id,
        jti=jti,
        expires_at=exp,
    )

    payload = {
        "user_id": user_id,
        "type": token_type,
        "jti": str(jti),
        "exp": exp,
    }

    return jwt.encode(payload, EMAIL_SECRET_KEY, algorithm=ALGORITHM)


def verify_password_reset_token(token) -> user_db:
    """Verify a password reset token and mark it as used."""

    try:
        payload = jwt.decode(
            token,
            EMAIL_SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        if payload.get("type") != "password_reset":
            raise ValueError("Invalid token type.")

        reset_token = PasswordResetToken.objects.select_related("user").get(
            jti=payload["jti"]
        )

        if reset_token.used_at is not None:
            raise ValueError("This reset link has already been used.")

        if reset_token.expires_at <= timezone.now():
            raise ValueError("Reset link has expired.")

        reset_token.used_at = timezone.now()
        reset_token.save(update_fields=["used_at"])

        return payload

    except PasswordResetToken.DoesNotExist as err:
        raise ValueError("Invalid password reset token.") from err

    except jwt.ExpiredSignatureError as err:
        raise ValueError("Reset link has expired.") from err

    except jwt.InvalidTokenError as err:
        raise ValueError("Invalid password reset token.") from err
