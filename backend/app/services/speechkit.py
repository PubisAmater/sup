"""
Сервис интеграции с Yandex SpeechKit для синтеза речи (Text-to-Speech).

ЧТО: Модуль предоставляет класс SpeechKitService, который преобразует текстовое
резюме совещания в аудиофайл формата OGG Opus с помощью Yandex SpeechKit API.

ЗАЧЕМ: Руководителям удобнее прослушать краткое аудиорезюме совещания в Telegram,
чем читать текст. Это экономит время и позволяет ознакомиться с итогами совещания
на ходу --- в машине, между встречами и т.д.

КАК: Используется REST API Yandex SpeechKit TTS v1. Текст отправляется POST-запросом
на endpoint синтеза, в ответ приходят сырые байты аудиофайла. Авторизация ---
через API-ключ сервисного аккаунта Yandex Cloud.

Параметры TTS по умолчанию:
  - voice: "filipp" --- мужской голос премиум-качества на русском языке.
    Доступные альтернативы: "alena" (женский), "ermil" (мужской), "jane" (женский),
    "omazh" (женский), "zahar" (мужской).
  - format: "oggopus" --- формат OGG с кодеком Opus. Выбран потому, что Telegram
    нативно поддерживает OGG Opus для голосовых сообщений и аудио, а также потому,
    что этот формат обеспечивает хорошее сжатие при высоком качестве звука.
  - language: "ru-RU" --- русский язык (Россия). SpeechKit также поддерживает
    "en-US", "tr-TR", "de-DE" и другие языки.
"""

import httpx

from app.config import get_settings

SPEECHKIT_TTS_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"


class SpeechKitService:
    """
    Сервис синтеза речи через Yandex SpeechKit API.

    ЧТО: Обёртка над Yandex SpeechKit TTS API, предоставляющая единственный метод
    text_to_speech() для преобразования текста в аудио.

    ЗАЧЕМ: Инкапсулирует детали авторизации (API-ключ, folder_id) и параметры
    запроса к SpeechKit, позволяя остальной части приложения просто передать текст
    и получить байты аудиофайла.

    КАК: При инициализации загружает API-ключ и folder_id из настроек приложения.
    folder_id --- это идентификатор каталога Yandex Cloud, к которому привязан
    сервисный аккаунт и квоты на использование SpeechKit.

    Атрибуты:
        api_key (str): API-ключ сервисного аккаунта Yandex Cloud для SpeechKit.
        folder_id (str): Идентификатор каталога (folder) в Yandex Cloud.
    """

    def __init__(self):
        """
        Инициализация сервиса SpeechKit.

        ЧТО: Загружает API-ключ и folder_id из конфигурации приложения.

        ЗАЧЕМ: API-ключ и folder_id необходимы для авторизации каждого запроса
        к Yandex SpeechKit API. Хранятся в переменных окружения SPEECHKIT_API_KEY
        и SPEECHKIT_FOLDER_ID соответственно.
        """
        settings = get_settings()
        self.api_key = settings.speechkit_api_key
        self.folder_id = settings.speechkit_folder_id

    async def text_to_speech(
        self,
        text: str,
        voice: str = "filipp",
        language: str = "ru-RU",
    ) -> bytes:
        """
        Синтезирует речь из текста и возвращает аудиофайл в виде байтов.

        ЧТО: Отправляет текст в Yandex SpeechKit TTS API и возвращает аудиофайл
        в формате OGG Opus.

        ЗАЧЕМ: Используется для генерации аудиорезюме совещаний, которое затем
        отправляется участникам в Telegram через TelegramBotService.send_audio().

        КАК работает:
          1. Формирует POST-запрос к SPEECHKIT_TTS_URL с параметрами:
             - text: текст для озвучивания (макс. ~5000 символов на один запрос).
             - lang: код языка (по умолчанию "ru-RU").
             - voice: имя голоса (по умолчанию "filipp" --- мужской, премиум).
             - folderId: идентификатор каталога Yandex Cloud.
             - format: "oggopus" --- формат выходного аудио.
          2. Авторизация через заголовок "Authorization: Api-Key <ключ>".
          3. Возвращает сырые байты ответа (response.content) --- это готовый
             аудиофайл, который можно сохранить или отправить в Telegram.

        Аргументы:
            text (str): Текст для синтеза речи. Рекомендуемая длина --- до 5000
                символов. Для более длинных текстов необходимо разбиение на части.
            voice (str): Имя голоса для синтеза. По умолчанию "filipp" --- мужской
                голос премиум-качества. Варианты: "alena", "ermil", "jane",
                "omazh", "zahar" и другие.
            language (str): Код языка в формате BCP-47. По умолчанию "ru-RU".
                Поддерживаются: "en-US", "tr-TR", "de-DE" и др.

        Возвращает:
            bytes: Сырые байты аудиофайла в формате OGG Opus. Готовы для отправки
            в Telegram или сохранения на диск.

        Исключения:
            httpx.HTTPStatusError: При ошибке API (невалидный ключ, превышение
            квоты, слишком длинный текст и т.д.).
        """
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
