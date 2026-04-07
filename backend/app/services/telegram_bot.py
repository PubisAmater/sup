"""
Сервис интеграции с Telegram Bot API для отправки уведомлений.

ЧТО: Модуль предоставляет класс TelegramBotService для отправки текстовых
сообщений и аудиофайлов в Telegram-чаты через Telegram Bot API.

ЗАЧЕМ: Telegram --- основной канал уведомлений для руководителей. После обработки
совещания система отправляет:
  1. Текстовое сообщение с резюме, списком решений и задач (HTML-разметка).
  2. Аудиофайл с озвученным резюме (OGG Opus, сгенерированный SpeechKitService).

КАК: Используется Telegram Bot API (https://api.telegram.org). Бот создаётся
через @BotFather, токен хранится в переменной окружения TELEGRAM_BOT_TOKEN.
Все запросы --- POST к endpoint-ам sendMessage и sendAudio.
"""

import httpx

from app.config import get_settings

TELEGRAM_API_URL = "https://api.telegram.org"


class TelegramBotService:
    """
    Сервис для отправки сообщений и аудио через Telegram Bot API.

    ЧТО: Обёртка над Telegram Bot API, предоставляющая два метода:
      - send_message() --- отправка текстового сообщения с HTML-разметкой.
      - send_audio() --- отправка аудиофайла с опциональной подписью.

    ЗАЧЕМ: Инкапсулирует формирование URL бота, авторизацию через токен и
    HTTP-запросы к Telegram API. Позволяет остальной части приложения просто
    вызвать send_message(chat_id, text) без знания деталей протокола.

    КАК: При инициализации формирует base_url вида
    "https://api.telegram.org/bot<TOKEN>", который используется как префикс
    для всех вызовов API. Каждый метод создаёт отдельный httpx.AsyncClient
    для выполнения POST-запроса.

    Атрибуты:
        bot_token (str): Токен Telegram-бота, полученный от @BotFather.
        base_url (str): Базовый URL для API-вызовов (включает токен).
    """

    def __init__(self):
        """
        Инициализация сервиса Telegram Bot.

        ЧТО: Загружает токен бота из конфигурации и формирует базовый URL.

        ЗАЧЕМ: Токен бота --- единственный способ авторизации в Telegram Bot API.
        Он хранится в переменной окружения TELEGRAM_BOT_TOKEN для безопасности.
        """
        settings = get_settings()
        self.bot_token = settings.telegram_bot_token
        self.base_url = f"{TELEGRAM_API_URL}/bot{self.bot_token}"

    async def send_message(self, chat_id: int, text: str, parse_mode: str = "HTML") -> dict:
        """
        Отправляет текстовое сообщение в Telegram-чат.

        ЧТО: Отправляет текстовое сообщение указанному пользователю или в группу
        через Telegram Bot API метод sendMessage.

        ЗАЧЕМ: Используется для отправки текстовых уведомлений --- резюме совещаний,
        списков задач, алертов по метрикам и других оповещений. HTML-разметка
        позволяет форматировать текст: <b>жирный</b>, <i>курсив</i>, <code>код</code>,
        <a href="...">ссылки</a>.

        КАК работает:
          1. Отправляет POST-запрос на /sendMessage с JSON-телом.
          2. Telegram обрабатывает HTML-теги в тексте (parse_mode="HTML").
          3. Возвращает ответ Telegram API --- словарь с полями "ok", "result"
             (содержит message_id, chat, date и др.).

        Аргументы:
            chat_id (int): Уникальный идентификатор чата или пользователя в Telegram.
                Можно получить через getUpdates API или из webhook-обновлений.
            text (str): Текст сообщения. Поддерживает HTML-разметку (если
                parse_mode="HTML") или Markdown (если parse_mode="Markdown").
                Максимальная длина --- 4096 символов (ограничение Telegram).
            parse_mode (str): Режим парсинга текста. По умолчанию "HTML".
                Варианты: "HTML", "Markdown", "MarkdownV2".

        Возвращает:
            dict: Ответ Telegram API. При успехе содержит {"ok": True, "result": {...}},
            где result --- объект отправленного сообщения.

        Исключения:
            httpx.HTTPStatusError: При ошибке Telegram API (бот заблокирован
            пользователем, невалидный chat_id, текст слишком длинный и т.д.).
        """
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
        """
        Отправляет аудиофайл в Telegram-чат.

        ЧТО: Отправляет аудиофайл (OGG Opus) указанному пользователю или в группу
        через Telegram Bot API метод sendAudio.

        ЗАЧЕМ: Используется для отправки аудиорезюме совещаний, сгенерированных
        через Yandex SpeechKit. Руководители могут прослушать краткое резюме
        прямо в Telegram, не читая текст.

        КАК работает:
          1. Формирует multipart/form-data запрос с двумя частями:
             - data: {"chat_id": ..., "caption": ...} --- метаданные.
             - files: {"audio": ("summary.ogg", bytes, "audio/ogg")} --- аудиофайл.
          2. Файл отправляется с именем "summary.ogg" и MIME-типом "audio/ogg".
             Telegram автоматически распознаёт OGG Opus и отображает встроенный
             аудиоплеер в чате.
          3. Возвращает ответ Telegram API с информацией об отправленном аудио.

        Аргументы:
            chat_id (int): Уникальный идентификатор чата или пользователя в Telegram.
            audio (bytes): Сырые байты аудиофайла в формате OGG Opus.
                Обычно получены из SpeechKitService.text_to_speech().
            caption (str): Текстовая подпись к аудиофайлу. Отображается под
                плеером в Telegram. По умолчанию пустая строка.

        Возвращает:
            dict: Ответ Telegram API. При успехе содержит {"ok": True, "result": {...}},
            где result --- объект отправленного аудиосообщения (включая file_id,
            duration, file_size).

        Исключения:
            httpx.HTTPStatusError: При ошибке Telegram API (файл слишком большой ---
            лимит 50 МБ для ботов, бот заблокирован, невалидный формат и т.д.).
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/sendAudio",
                data={"chat_id": chat_id, "caption": caption},
                files={"audio": ("summary.ogg", audio, "audio/ogg")},
            )
            response.raise_for_status()
            return response.json()
