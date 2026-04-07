import httpx

from app.config import get_settings

TELEGRAM_API_URL = "https://api.telegram.org"


class TelegramBotService:
    def __init__(self):
        settings = get_settings()
        self.bot_token = settings.telegram_bot_token
        self.base_url = f"{TELEGRAM_API_URL}/bot{self.bot_token}"

    async def send_message(self, chat_id: int, text: str, parse_mode: str = "HTML") -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                },
            )
            response.raise_for_status()
            return response.json()

    async def send_audio(self, chat_id: int, audio: bytes, caption: str = "") -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/sendAudio",
                data={"chat_id": chat_id, "caption": caption},
                files={"audio": ("summary.ogg", audio, "audio/ogg")},
            )
            response.raise_for_status()
            return response.json()
