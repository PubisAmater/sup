# СУП — Система Управления Персоналом

Интеллектуальная мультитенантная SaaS-платформа управления персоналом.
Трансформирует статическую базу знаний в активный инструмент контроля исполнения.

## Технологический стек

| Компонент | Технология |
|-----------|-----------|
| Backend | Python 3.12 + FastAPI |
| Frontend | Next.js 14 + TypeScript + Tailwind CSS |
| Telegram Bot | Python 3.12 + aiogram 3 |
| БД | PostgreSQL 16 (мультитенантность через RLS) |
| Очереди | Redis + arq |
| TTS | Яндекс SpeechKit |
| LLM | Claude API |
| Авторизация | Telegram OAuth + JWT |

## Быстрый старт

```bash
# 1. Скопируйте переменные окружения
cp .env.example .env
# Заполните значения в .env

# 2. Запустите все сервисы
docker compose up -d

# 3. Примените миграции
docker compose exec backend alembic upgrade head
```

Backend API: http://localhost:8000/docs
Frontend: http://localhost:3000

## Разработка

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:create_app --factory --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Bot
```bash
cd bot
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m bot.main
```

## Структура проекта

```
sup/
├── backend/          # FastAPI backend
│   ├── app/          # Application code
│   │   ├── api/      # REST endpoints
│   │   ├── auth/     # Authentication (Telegram + JWT)
│   │   ├── models/   # SQLAlchemy models
│   │   ├── schemas/  # Pydantic schemas
│   │   ├── services/ # External service integrations
│   │   └── workers/  # Background task workers
│   ├── alembic/      # Database migrations
│   └── tests/        # Backend tests
├── frontend/         # Next.js frontend
│   └── src/
│       ├── app/      # Pages (App Router)
│       ├── components/
│       └── lib/      # Utilities
└── bot/              # Telegram bot (aiogram)
```

## Архитектура

- **Мультитенантность** — tenant_id + PostgreSQL Row Level Security
- **API-first** — веб и бот = клиенты REST API
- **Иерархия ролей** — SuperAdmin → CEO → CEO-1 → CEO-2 → Middle → Line
