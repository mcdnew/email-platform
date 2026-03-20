# app/tracking.py — token serializer for unsubscribe links
#
# Uses itsdangerous URLSafeSerializer to sign email addresses into
# tamper-proof tokens. The token is embedded in unsubscribe links and
# verified by the /unsubscribe endpoint.

from itsdangerous import URLSafeSerializer, BadSignature
from app.config import settings

serializer = URLSafeSerializer(settings.API_KEY or "dev-secret-change-in-production")


def make_unsubscribe_token(email: str) -> str:
    return serializer.dumps(email)


def load_unsubscribe_token(token: str) -> str | None:
    """Return the email address or None if the token is invalid."""
    try:
        return serializer.loads(token)
    except BadSignature:
        return None
