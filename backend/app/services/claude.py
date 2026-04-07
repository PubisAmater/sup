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
    def __init__(self):
        settings = get_settings()
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def analyze_meeting(
        self,
        transcript: str,
        participants_context: str | None = None,
        historical_decisions: str | None = None,
        open_tasks: str | None = None,
    ) -> MeetingAnalysisResult:
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
