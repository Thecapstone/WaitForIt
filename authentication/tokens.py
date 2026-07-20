"""Custom JWT authentication backend handling cookie-based tokens."""

import datetime
import hashlib
import os
from uuid import uuid4

from ipware import get_client_ip
import jwt
from rest_framework import permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from user_agents.parsers import parse

from authentication.models import PasswordResetToken, User as user_db

ACCESS_SECRET = os.getenv("ACCESS_SECRET")
SESSION_SECRET = os.getenv("SESSION_SECRET")
EMAIL_SECRET_KEY = os.getenv("Email_Key")

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


def create_user_agent(u_agent: str, ip: str) -> str:
    """Generate a stable, hashed device fingerprint from IP and User Agent."""
    ip_addr = ".".join(ip.split(".")[:2])
    user_agent = parse(u_agent)
    stable_string = f"{user_agent.os.family}--{user_agent.browser.family}--{user_agent.is_mobile}--{ip_addr}"

    return hashlib.sha256(stable_string.encode("utf-8")).hexdigest()


class HasBootstrapToken(permissions.BasePermission):
    """Allows access only if the client provides the correct secret master key."""

    def is_allowed(self, request, view):
        # Fetch the secret token from the server environment
        secret_key = os.environ.get("ADMIN_BOOTSTRAP_TOKEN")
        admin_token = jwt.encode({"key": secret_key}, "admin_key", algorithm="HS256")
        if not secret_key:
            return False  # Secure by default if env variable is missing

        # Check for matching HTTP Header (e.g., 'X-Bootstrap-Token: my-secret-key')
        client_token = request.headers.get("X-Bootstrap-Token")
        hashed_cookie = jwt.encode(
            {"key": client_token}, "admin_key", algorithm="HS256"
        )
        return hashed_cookie == admin_token


def session_token(user_id: int, role: str, session_version: int, request) -> str:
    """Build and hash a tracking payload tracking user session versions."""
    active_devices = create_user_agent(user_agent, ip_address)
    _ip_address, _ = get_client_ip(request)
    request.META.get("HTTP_USER_AGENT", "")
    hashlib.sha256(uuid4().bytes).hexdigest()
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
        role = session_payload.get("role")

        if not user_id or not role:
            raise ValueError("Invalid session token payload data.")

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

    except jwt.ExpiredSignatureError:
        raise ValueError("Session token has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid session token.")


def generate_token(user_id, exp, token_type) -> str:
    """Generate a unique token for email verification and password reset."""
    jti = str(uuid4())
    payload = {
        "user_id": user_id,
        "type": token_type,
        "jti": jti,
        "exp": exp,
    }
    return jwt.encode(payload, EMAIL_SECRET_KEY, algorithm=ALGORITHM)


def generate_password_reset_token(user, exp, token_type) -> str:
    """Generate and persist a one-time password reset token."""

    jti = uuid4()

    PasswordResetToken.objects.create(
        user=user,
        jti=jti,
        expires_at=exp,
    )

    payload = {
        "user_id": user.id,
        "type": token_type,
        "jti": str(jti),
        "exp": exp,
    }

    return jwt.encode(payload, EMAIL_SECRET_KEY, algorithm=ALGORITHM)


def verify_verification_token(token) -> str:
    """Verify user account using email token"""
    try:
        payload = jwt.decode(token, EMAIL_SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "email_verification":
            raise ValueError("Invalid token type.")
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired.")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token.")


from django.utils import timezone


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

        return reset_token.user

    except PasswordResetToken.DoesNotExist:
        raise ValueError("Invalid password reset token.")

    except jwt.ExpiredSignatureError as err:
        raise ValueError("Reset link has expired.") from err

    except jwt.InvalidTokenError as err:
        raise ValueError("Invalid password reset token.") from err
