import hashlib
import hmac
from typing import Any

from pydantic import BaseModel

from app.config import get_settings


class TelegramAuthData(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


def verify_telegram_auth(data: dict[str, Any]) -> bool:
    settings = get_settings()
    if not settings.telegram_bot_token:
        return False

    check_hash = data.pop("hash", "")
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(data.items()) if v is not None
    )

    secret_key = hashlib.sha256(settings.telegram_bot_token.encode()).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    data["hash"] = check_hash
    return hmac.compare_digest(computed_hash, check_hash)
