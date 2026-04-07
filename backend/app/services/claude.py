import anthropic

from app.config import get_settings

MEETING_SUMMARY_PROMPT = """Ты — ИИ-ассистент для обработки протоколов совещаний.

Проанализируй транскрипцию и выдели:
1. Ключевые решения (с указанием ответственных)
2. Поставленные задачи (исполнитель, срок)
3. Основные тезисы обсуждения
4. Проблемные моменты и риски
5. Процент «воды» в разговоре

Формат ответа — структурированный JSON."""


class ClaudeService:
    def __init__(self):
        settings = get_settings()
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def summarize_meeting(
        self, transcript: str, context: str | None = None
    ) -> str:
        system_prompt = MEETING_SUMMARY_PROMPT
        if context:
            system_prompt += f"\n\nКонтекст (участники, роли, открытые задачи):\n{context}"

        message = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": transcript}],
        )
        return message.content[0].text
