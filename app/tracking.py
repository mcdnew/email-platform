# app/tracking.py — token serializer for unsubscribe links
#
# Uses itsdangerous URLSafeSerializer to sign email addresses into
# tamper-proof tokens. The token is embedded in unsubscribe links and
# verified by the /unsubscribe endpoint.
#
# Uses UNSUBSCRIBE_SECRET (dedicated key) so rotating API_KEY does not
# invalidate unsubscribe links already embedded in sent emails.
# Falls back to API_KEY for backward compatibility when UNSUBSCRIBE_SECRET
# is not set.

from itsdangerous import URLSafeSerializer, BadSignature
from app.config import settings

_secret = settings.UNSUBSCRIBE_SECRET or settings.API_KEY or "dev-secret-change-in-production"
serializer = URLSafeSerializer(_secret, salt="unsubscribe")


def make_unsubscribe_token(email: str) -> str:
    return serializer.dumps(email)


def load_unsubscribe_token(token: str) -> str | None:
    """Return the email address or None if the token is invalid."""
    try:
        return serializer.loads(token)
    except BadSignature:
        return None
