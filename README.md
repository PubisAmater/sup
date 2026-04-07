# СУП — Система Управления Персоналом

Интеллектуальная мультитенантная SaaS-платформа управления персоналом.
Трансформирует статическую базу знаний в активный инструмент контроля исполнения.
Предназначена для CEO и топ-менеджмента, с масштабированием на всех сотрудников.

**Первый клиент:** ГК «Диадент» — сеть стоматологических клиник, Санкт-Петербург.
5 филиалов, ~170 сотрудников, до 10 топ-менеджеров.

---

## Архитектура

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend      │     │  Telegram    │     │  Telegram    │
│   (Next.js)     │     │  Bot         │     │  OAuth       │
│   Vercel CDN    │     │  (aiogram)   │     │  Login       │
└───────┬─────────┘     └──────┬───────┘     └──────┬───────┘
        │                      │                     │
        └──────────┬───────────┘                     │
                   │  REST API (JWT Bearer)          │
        ┌──────────▼──────────────────────────────────▼──┐
        │              Backend (FastAPI)                  │
        │  /auth  /api/v1/meetings  /api/v1/tasks  ...  │
        │  JWT + PostgreSQL RLS мультитенантность         │
        └──────┬────────────┬───────────────┬────────────┘
               │            │               │
        ┌──────▼──┐  ┌──────▼──────┐  ┌─────▼─────┐
        │ Postgres │  │   Redis     │  │  Workers  │
        │ 16 + RLS │  │ (arq queue) │  │  (arq)    │
        └─────────┘  └─────────────┘  └─────┬─────┘
                                             │
                    ┌────────────────────────┬┴──────────────┐
                    │                        │               │
              ┌─────▼─────┐          ┌───────▼───┐    ┌──────▼──────┐
              │ Claude API │          │  Notion   │    │  SpeechKit  │
              │ (анализ    │          │  (синхр.) │    │  (аудио)    │
              │ совещаний) │          └───────────┘    └─────────────┘
              └────────────┘
```

---

## Технологический стек

| Компонент | Технология | Назначение |
|-----------|-----------|-----------|
| Backend | Python 3.12 + FastAPI | REST API, бизнес-логика |
| Frontend | Next.js 14 + TypeScript + Tailwind CSS | Веб-интерфейс (Vercel) |
| Telegram Bot | Python 3.12 + aiogram 3 | Уведомления, команды CEO |
| БД | PostgreSQL 16 | Хранение данных + RLS мультитенантность |
| Очереди | Redis + arq | Фоновые задачи (анализ, синхронизация) |
| TTS | Яндекс SpeechKit | Аудио-саммари отчётов (голос «Филипп») |
| LLM | Claude API (Sonnet) | Анализ совещаний, извлечение решений |
| Авторизация | Telegram OAuth + JWT (HS256) | Вход через Telegram |
| CI/CD | GitHub Actions | Автотесты при push |
| Хостинг | Vercel (frontend) + VPS (backend) | Деплой |

---

## Модули системы

### 1. Мультитенантность
- PostgreSQL Row Level Security (RLS) на всех таблицах (кроме tenants)
- `tenant_id` в каждой строке каждой таблицы
- Контекст тенанта устанавливается через `SET app.current_tenant` в начале каждого запроса
- Один экземпляр приложения обслуживает множество компаний

### 2. Обработка совещаний — ИИ
- Загрузка транскрипции из Plaud
- Анализ через Claude API → структурированный JSON:
  - Решения (с ответственными и сроками)
  - Задачи (с исполнителями и приоритетами)
  - Ключевые тезисы, риски, % «воды»
- Сравнение новых решений с архивом (90 дней) на противоречия
- Синхронизация в Notion (совещания, решения, задачи)

### 3. Еженедельная отчётность
- Топ-менеджеры подают через веб-форму
- Доставка CEO в Telegram по блокам
- Аудио-саммари через Яндекс SpeechKit

### 4. Веб-платформа
- 8 разделов: Дашборд, Сотрудники, Совещания, Задачи, Отчёты, Календарь, Метрики, Рейтинг
- Бронирование слотов в календаре CEO (Google Calendar)

### 5. ИИ-Анализатор метрик
- Мониторинг метрик из Dental Pro, 1С, Bitrix24
- Алерты при отклонениях (threshold, deviation, trend)
- Формула выручки: Кресла × Загрузка × Средний чек

### 6. Балльно-рейтинговая система
- Автобаллы: задача в срок (+5), просрочка (-3), отчёт вовремя (+3)
- Ручные штрафы/премии CEO
- Peer-review (раз в 2 недели)
- Лидерборд

---

## Иерархия ролей

```
SuperAdmin (0)  — доступ ко всем тенантам
    └── CEO (1)  — полный доступ к своему тенанту
        ├── CEO-1 (2)  — директора направлений
        │   └── CEO-2 (3)  — руководители отделов
        │       └── Middle (4)  — средний менеджмент
        │           └── Line (5)  — линейные сотрудники
```

---

## База данных (12 таблиц)

| Таблица | Описание | RLS |
|---------|----------|-----|
| tenants | Компании-клиенты | Нет |
| users | Учётные записи (Telegram OAuth) | Да |
| employees | Кадровые записи | Да |
| meetings | Совещания (протоколы) | Да |
| meeting_participants | Участники совещаний (M2M) | Да |
| decisions | Решения совещаний | Да |
| tasks | Задачи | Да |
| weekly_reports | Еженедельные отчёты | Да |
| metric_snapshots | Снимки бизнес-метрик | Да |
| metric_alerts | Алерты при отклонениях | Да |
| score_entries | Баллы рейтинговой системы | Да |
| peer_reviews | Peer-review оценки | Да |

---

## API Endpoints

Полная Swagger документация: `http://localhost:8000/docs`

### Авторизация
- `POST /auth/telegram/callback` — Вход через Telegram OAuth → JWT
- `GET /auth/me` — Текущий пользователь

### Совещания
- `GET /api/v1/meetings/` — Список (фильтры: status, date, organizer)
- `POST /api/v1/meetings/` — Создать совещание
- `GET /api/v1/meetings/{id}` — Детали (с решениями)
- `POST /api/v1/meetings/{id}/transcript` — Загрузить транскрипцию → AI анализ
- `POST /api/v1/meetings/{id}/analyze` — Повторный AI анализ
- `GET /api/v1/meetings/{id}/analysis` — Результат (решения + задачи + summary)

### Задачи
- `GET /api/v1/tasks/` — Список (фильтры: status, priority, assignee, meeting)
- `GET /api/v1/tasks/overdue` — Просроченные задачи

### Отчёты, Метрики, Рейтинг, Календарь
- `POST /api/v1/reports/{id}/submit` — Подать отчёт → доставка CEO в TG + аудио
- `GET /api/v1/metrics/revenue-formula` — Формула выручки
- `GET /api/v1/metrics/alerts` — Активные алерты
- `GET /api/v1/scores/leaderboard` — Рейтинг сотрудников
- `POST /api/v1/scores/bonus` / `penalty` — Бонус/штраф (CEO)
- `GET /api/v1/calendar/slots` — Свободные слоты CEO
- `GET /api/v1/dashboard/stats` — Статистика для дашборда

---

## Быстрый старт

### Docker Compose
```bash
cp .env.example .env   # Заполнить API ключи
docker compose up -d
docker compose exec backend alembic upgrade head
```

### Локальная разработка
```bash
# Backend
cd backend && pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:create_app --factory --reload

# Frontend
cd frontend && npm install && npm run dev

# Bot
cd bot && pip install -e . && python -m bot.main

# Workers
cd backend && arq app.workers.tasks.WorkerSettings
```

---

## Переменные окружения

Полный список — см. `.env.example`. Ключевые:

| Переменная | Описание |
|-----------|----------|
| DATABASE_URL | PostgreSQL (asyncpg) |
| SECRET_KEY | Ключ подписи JWT (сменить!) |
| TELEGRAM_BOT_TOKEN | Токен бота из @BotFather |
| ANTHROPIC_API_KEY | Claude API ключ |
| NOTION_API_KEY | Notion Integration Token |
| SPEECHKIT_API_KEY | Яндекс SpeechKit |

---

## Формула выручки

```
Выручка = Кресла × Загрузка% × Средний чек × 22 дня × 8 часов
```

Нормы: стоматологическое кресло 3 млн ₽/мес, целевая загрузка 85-90%.

---

© 2026 СУП. Все права защищены.
