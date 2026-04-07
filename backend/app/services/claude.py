"""
Сервис интеграции с Anthropic Claude API для анализа совещаний.

ЧТО: Модуль предоставляет класс ClaudeService, который отправляет транскрипцию
совещания в Claude API и получает структурированный JSON-ответ с резюме,
решениями, задачами, рисками и обнаруженными противоречиями.

ЗАЧЕМ: Автоматизация обработки протоколов совещаний --- вместо ручного разбора
многочасовых записей система за секунды извлекает ключевые решения, назначает
задачи с приоритетами и выявляет противоречия с ранее принятыми решениями.

КАК: Используются два промпта:
  1. MEETING_ANALYSIS_PROMPT --- системный промпт для основного анализа транскрипции.
     Задаёт роль модели и описывает требуемый формат JSON-ответа.
  2. CONTRADICTION_CHECK_PROMPT --- промпт для сравнения новых решений с архивом
     решений за последние 90 дней и поиска логических противоречий.

Оба промпта требуют ответа СТРОГО в формате JSON без markdown-обёрток.
Если модель всё же вернёт markdown-обёртку (```json ... ```), она автоматически
снимается перед парсингом.

Формат JSON-ответа MEETING_ANALYSIS_PROMPT:
  - summary (str): Краткое резюме совещания в 2-3 предложениях.
  - decisions (list[dict]): Принятые решения. Каждое решение содержит:
      - content (str): Текст решения.
      - responsible_name (str | null): Имя ответственного как в транскрипции.
      - due_date_hint (str | null): Упомянутый срок выполнения.
  - tasks (list[dict]): Поставленные задачи. Каждая задача содержит:
      - title (str): Краткое название задачи.
      - description (str): Подробное описание.
      - assignee_name (str | null): Имя исполнителя как в транскрипции.
      - priority (str): Приоритет --- "high", "medium" или "low".
      - due_date_hint (str | null): Упомянутый срок.
  - key_points (list[str]): Ключевые тезисы обсуждения.
  - risks (list[str]): Выявленные риски и проблемные моменты.
  - water_percentage (float): Процент «воды» (нерелевантного разговора), от 0 до 100.
  - contradictions (list[dict]): Противоречия с архивом (если передан). Каждое:
      - new_decision (str): Текст нового решения.
      - old_decision (str): Текст противоречащего старого решения.
      - explanation (str): Описание, в чём именно противоречие.
"""

import json
import logging

import anthropic

from app.config import get_settings
from app.schemas.meeting import MeetingAnalysisResult

logger = logging.getLogger(__name__)

MEETING_ANALYSIS_PROMPT = """Ты — ИИ-ассистент для обработки протоколов совещаний компании.

Проанализируй транскрипцию совещания и верни результат СТРОГО в формате JSON (без markdown, без ```):

{
  "summary": "Краткое резюме совещания (2-3 предложения)",
  "decisions": [
    {
      "content": "Текст решения",
      "responsible_name": "Имя ответственного (как в транскрипции)",
      "due_date_hint": "Упомянутый срок или null"
    }
  ],
  "tasks": [
    {
      "title": "Краткое название задачи",
      "description": "Подробное описание",
      "assignee_name": "Имя исполнителя (как в транскрипции)",
      "priority": "high/medium/low",
      "due_date_hint": "Упомянутый срок или null"
    }
  ],
  "key_points": ["Тезис 1", "Тезис 2"],
  "risks": ["Риск или проблемный момент"],
  "water_percentage": 15.5,
  "contradictions": [
    {
      "new_decision": "Новое решение",
      "old_decision": "Противоречащее старое решение",
      "explanation": "В чём противоречие"
    }
  ]
}

Правила:
- water_percentage: оценка доли нерелевантного разговора (0-100)
- Если решение или задача не имеет явного срока, ставь due_date_hint: null
- Если ответственный не указан, ставь responsible_name/assignee_name: null
- contradictions: сравни с предоставленным архивом решений. Если архива нет — пустой массив
- Возвращай ТОЛЬКО JSON, без пояснений"""

CONTRADICTION_CHECK_PROMPT = """Сравни новые решения с архивом предыдущих решений.
Найди противоречия, конфликты и несоответствия.

Новые решения:
{new_decisions}

Архив решений (последние 90 дней):
{historical_decisions}

Верни JSON массив противоречий (или пустой массив если их нет):
[
  {{
    "new_decision": "текст нового решения",
    "old_decision": "текст старого решения",
    "explanation": "в чём противоречие"
  }}
]

Возвращай ТОЛЬКО JSON массив."""


class ClaudeService:
    """
    Сервис для взаимодействия с Anthropic Claude API.

    ЧТО: Обёртка над асинхронным клиентом Anthropic, предоставляющая два основных метода:
      - analyze_meeting() --- полный анализ транскрипции совещания.
      - check_contradictions() --- поиск противоречий между новыми и старыми решениями.

    ЗАЧЕМ: Инкапсулирует логику формирования промптов, отправки запросов к Claude API,
    парсинга JSON-ответов и обработки ошибок. Позволяет остальной части приложения
    работать с типизированными объектами (MeetingAnalysisResult), а не с сырым текстом.

    КАК: При инициализации создаёт асинхронный клиент anthropic.AsyncAnthropic
    с API-ключом из настроек приложения. Все запросы используют модель
    claude-sonnet-4-20250514 (баланс между скоростью и качеством).

    Атрибуты:
        client (anthropic.AsyncAnthropic): Асинхронный HTTP-клиент для Anthropic API.
    """

    def __init__(self):
        """
        Инициализация сервиса Claude.

        ЧТО: Создаёт асинхронный клиент Anthropic с API-ключом из конфигурации.

        ЗАЧЕМ: API-ключ хранится в настройках приложения (переменная окружения
        ANTHROPIC_API_KEY) и подтягивается через get_settings() для безопасности.
        """
        settings = get_settings()
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def analyze_meeting(
        self,
        transcript: str,
        participants_context: str | None = None,
        historical_decisions: str | None = None,
        open_tasks: str | None = None,
    ) -> MeetingAnalysisResult:
        """
        Анализирует транскрипцию совещания и возвращает структурированный результат.

        ЧТО: Отправляет транскрипцию совещания в Claude API с системным промптом
        MEETING_ANALYSIS_PROMPT и опциональным контекстом (участники, архив решений,
        открытые задачи). Получает JSON-ответ, парсит его и возвращает объект
        MeetingAnalysisResult.

        ЗАЧЕМ: Это основной метод сервиса --- он превращает неструктурированный текст
        транскрипции в структурированные данные: резюме, решения, задачи, риски.
        Эти данные затем сохраняются в БД и синхронизируются в Notion.

        КАК работает алгоритм:
          1. Берёт базовый системный промпт MEETING_ANALYSIS_PROMPT.
          2. Если передан дополнительный контекст (участники, архив решений, открытые
             задачи), добавляет его к системному промпту через секцию "Контекст".
          3. Отправляет запрос к Claude API (модель claude-sonnet-4-20250514, max_tokens=4096).
             Транскрипция передаётся как user-сообщение.
          4. Получает текстовый ответ, снимает возможные markdown-обёртки (```json...```).
          5. Парсит JSON и создаёт MeetingAnalysisResult.
          6. При ошибке парсинга JSON --- возвращает fallback-результат с сырым текстом
             в поле summary (обрезанным до 2000 символов) и пустыми списками.
          7. При других ошибках API --- логирует и пробрасывает исключение выше.

        Аргументы:
            transcript (str): Полный текст транскрипции совещания.
            participants_context (str | None): Строка с описанием участников и их ролей.
                Помогает модели корректно атрибутировать решения и задачи.
            historical_decisions (str | None): Архив решений за последние 90 дней.
                Используется для поиска противоречий с новыми решениями.
            open_tasks (str | None): Список текущих открытых задач.
                Помогает модели не дублировать уже существующие задачи.

        Возвращает:
            MeetingAnalysisResult: Структурированный результат анализа совещания.

        Исключения:
            Exception: Пробрасывается при ошибках Claude API (кроме JSONDecodeError,
            который обрабатывается внутри и возвращает fallback-результат).
        """
        system_prompt = MEETING_ANALYSIS_PROMPT

        context_parts = []
        if participants_context:
            context_parts.append(f"Участники и их роли:\n{participants_context}")
        if historical_decisions:
            context_parts.append(f"Архив решений (90 дней):\n{historical_decisions}")
        if open_tasks:
            context_parts.append(f"Открытые задачи:\n{open_tasks}")

        if context_parts:
            system_prompt += "\n\nКонтекст:\n" + "\n\n".join(context_parts)

        try:
            message = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": transcript}],
            )
            raw_text = message.content[0].text

            # Убираем возможные markdown-обёртки
            text = raw_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            data = json.loads(text)
            return MeetingAnalysisResult(**data)

        except json.JSONDecodeError as e:
            logger.error("Failed to parse Claude response as JSON: %s", e)
            # Возвращаем базовый результат с сырым текстом как summary
            return MeetingAnalysisResult(
                summary=raw_text[:2000],
                decisions=[],
                tasks=[],
                key_points=[],
                risks=[],
                water_percentage=0,
                contradictions=[],
            )
        except Exception as e:
            logger.error("Claude API error: %s", e)
            raise

    async def check_contradictions(
        self,
        new_decisions: list[str],
        historical_decisions: list[str],
    ) -> list[dict]:
        """
        Проверяет новые решения на противоречия с архивом предыдущих решений.

        ЧТО: Отправляет в Claude API два списка --- новые решения и исторический архив
        решений за 90 дней --- и получает JSON-массив найденных противоречий.

        ЗАЧЕМ: Руководители часто принимают решения, которые противоречат ранее
        принятым. Этот метод автоматически выявляет такие конфликты, чтобы
        обратить на них внимание до того, как они приведут к проблемам.

        КАК работает алгоритм:
          1. Если архив решений пуст --- сразу возвращает пустой список (сравнивать не с чем).
          2. Форматирует оба списка решений в маркированные списки (- решение).
          3. Подставляет их в шаблон CONTRADICTION_CHECK_PROMPT.
          4. Отправляет запрос к Claude API (модель claude-sonnet-4-20250514, max_tokens=2048).
          5. Снимает возможные markdown-обёртки с ответа.
          6. Парсит JSON-массив и возвращает список словарей с полями:
             - new_decision (str): текст нового решения.
             - old_decision (str): текст старого противоречащего решения.
             - explanation (str): описание, в чём конкретно состоит противоречие.
          7. При любой ошибке (сеть, парсинг, API) --- логирует и возвращает пустой список.

        Аргументы:
            new_decisions (list[str]): Список текстов новых решений, принятых на совещании.
            historical_decisions (list[str]): Список текстов решений из архива за 90 дней.

        Возвращает:
            list[dict]: Список найденных противоречий. Каждый элемент --- словарь
            с ключами "new_decision", "old_decision", "explanation".
            Пустой список, если противоречий нет или произошла ошибка.
        """
        if not historical_decisions:
            return []

        prompt = CONTRADICTION_CHECK_PROMPT.format(
            new_decisions="\n".join(f"- {d}" for d in new_decisions),
            historical_decisions="\n".join(f"- {d}" for d in historical_decisions),
        )

        try:
            message = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            text = message.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            return json.loads(text)
        except Exception as e:
            logger.error("Contradiction check failed: %s", e)
            return []
