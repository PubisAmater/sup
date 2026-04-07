import httpx

from app.config import get_settings

SPEECHKIT_TTS_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"


class SpeechKitService:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.speechkit_api_key
        self.folder_id = settings.speechkit_folder_id

    async def text_to_speech(
        self,
        text: str,
        voice: str = "filipp",
        language: str = "ru-RU",
    ) -> bytes:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                SPEECHKIT_TTS_URL,
                headers={"Authorization": f"Api-Key {self.api_key}"},
                data={
                    "text": text,
                    "lang": language,
                    "voice": voice,
                    "folderId": self.folder_id,
                    "format": "oggopus",
                },
            )
            response.raise_for_status()
            return response.content
