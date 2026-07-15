"""Custom JWT authentication backend handling cookie-based tokens."""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed


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
            raise AuthenticationFailed(f"Token validation failed:{str(e)}") from e
        try:
            user = self.get_user(validated_token)
            return user, validated_token
        except AuthenticationFailed as e:
            raise AuthenticationFailed(f"Error retrieving user: {str(e)}") from e
