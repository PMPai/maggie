import json
import time
import uuid
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from app.config import get_settings

settings = get_settings()
_serializer = URLSafeTimedSerializer(settings.APP_SECRET, salt="auth-tokens")


def create_access_token(user_id: uuid.UUID, org_id: uuid.UUID, roles: list) -> str:
    payload = {
        "sub": str(user_id),
        "org": str(org_id),
        "roles": [r.value if hasattr(r, "value") else r for r in roles],
        "type": "access",
        "iat": int(time.time()),
    }
    return _serializer.dumps(payload)


def create_refresh_token(user_id: uuid.UUID) -> str:
    payload = {"sub": str(user_id), "type": "refresh", "iat": int(time.time())}
    return _serializer.dumps(payload)


def decode_token(token: str, max_age: int) -> dict:
    try:
        return _serializer.loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
