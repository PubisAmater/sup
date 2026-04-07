"""Seed database with demo data for Diadent dental clinic."""
import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory, engine
from app.models import *


async def seed():
    async with async_session_factory() as s:
        # Tenant
        tenant_id = uuid.uuid4()
        s.add(Tenant(id=tenant_id, name="ГК Диадент", slug="diadent"))
        await s.flush()

        # Users
        users = {}
        user_data = [
            ("ceo", "Роман", "Райт", 100001),
            ("ceo_1", "Анна", "Петрова", 100002),
            ("ceo_1", "Дмитрий", "Козлов", 100003),
            ("ceo_2", "Елена", "Сидорова", 100004),
            ("ceo_2", "Михаил", "Волков", 100005),
            ("middle", "Ольга", "Новикова", 100006),
            ("middle", "Сергей", "Морозов", 100007),
            ("middle", "Ирина", "Васильева", 100008),
            ("line", "Алексей", "Попов", 100009),
            ("line", "Марина", "Лебедева", 100010),
        ]
        for role, first, last, tg_id in user_data:
            uid = uuid.uuid4()
            s.add(User(id=uid, tenant_id=tenant_id, telegram_id=tg_id,
                       first_name=first, last_name=last, role=role, username=f"{first.lower()}_{last.lower()}"))
            users[f"{first} {last}"] = uid
        await s.flush()

        # Employees
        departments = [
            ("Анна Петрова", "Директор по маркетингу", "Маркетинг"),
            ("Дмитрий Козлов", "Финансовый директор", "Финансы"),
            ("Елена Сидорова", "Руководитель HR", "HR"),
            ("Михаил Волков", "Главный врач", "Клиника"),
            ("Ольга Новикова", "Менеджер по продажам", "Продажи"),
            ("Сергей Морозов", "Администратор филиала", "Клиника"),
            ("Ирина Васильева", "Бухгалтер", "Финансы"),
            ("Алексей Попов", "Стоматолог-терапевт", "Клиника"),
            ("Марина Лебедева", "Ассистент стоматолога", "Клиника"),
        ]
        for name, pos, dept in departments:
            s.add(Employee(id=uuid.uuid4(), tenant_id=tenant_id, user_id=users[name],
                           position=pos, department=dept, hired_at=date(2024, 1, 15)))
        await s.flush()

        # Meetings
        now = datetime.now()
        meetings = []
        meeting_data = [
            ("Стратегическая сессия Q2 2026", "Обсуждение целей и KPI на второй квартал", -7, 120, "completed"),
            ("Еженедельное совещание руководства", "Обзор текущих показателей и задач", -2, 60, "completed"),
            ("Планёрка по маркетингу", "Обсуждение рекламных кампаний и бюджета", -1, 45, "completed"),
            ("Обзор финансовых показателей", "Месячный отчёт по выручке и расходам", 0, 60, "scheduled"),
            ("Совещание по HR-процессам", "Обновление процессов найма и адаптации", 1, 45, "scheduled"),
            ("Планирование расширения филиала", "Открытие нового филиала на Петроградской", 3, 90, "scheduled"),
        ]
        for title, desc, days_offset, dur, status in meeting_data:
            mid = uuid.uuid4()
            organizer = list(users.values())[0]  # CEO
            processing = "completed" if status == "completed" else "pending"
            summary_text = None
            if status == "completed":
                summary_text = f"На совещании «{title}» обсуждались ключевые вопросы. Приняты решения по оптимизации процессов и распределению ресурсов."

            s.add(Meeting(id=mid, tenant_id=tenant_id, title=title, description=desc,
                          scheduled_at=now + timedelta(days=days_offset),
                          duration_minutes=dur, organizer_id=organizer, status=status,
                          processing_status=processing, summary=summary_text))
            meetings.append(mid)
        await s.flush()

        # Decisions
        decisions_data = [
            (meetings[0], "Увеличить бюджет на цифровой маркетинг на 30%", "high", date(2026, 4, 30)),
            (meetings[0], "Внедрить CRM-аналитику для отслеживания конверсии", "medium", date(2026, 5, 15)),
            (meetings[1], "Провести аудит загрузки кресел по всем филиалам", "high", date(2026, 4, 14)),
            (meetings[1], "Подготовить план обучения для новых сотрудников", "medium", date(2026, 4, 21)),
            (meetings[2], "Запустить таргетированную рекламу на Яндекс.Директ", "high", date(2026, 4, 12)),
            (meetings[2], "Обновить контент на сайте — кейсы и отзывы", "low", date(2026, 4, 25)),
        ]
        for mid, content, priority, due in decisions_data:
            s.add(Decision(id=uuid.uuid4(), tenant_id=tenant_id, meeting_id=mid,
                           content=content, decided_by=list(users.values())[0],
                           assignee_id=list(users.values())[1], priority=priority,
                           due_date=due, status="active"))
        await s.flush()

        # Tasks
        tasks_data = [
            ("Настроить Яндекс.Директ кампанию", "Создать и запустить рекламные кампании", 1, "high", "in_progress", date(2026, 4, 12), meetings[2]),
            ("Подготовить финансовый отчёт за март", "Собрать данные из 1С, сформировать отчёт", 2, "high", "done", date(2026, 4, 5), meetings[1]),
            ("Аудит загрузки кресел", "Проанализировать данные из Dental Pro по всем филиалам", 3, "high", "in_progress", date(2026, 4, 14), meetings[1]),
            ("Обновить HR-процессы", "Описать процесс онбординга новых сотрудников", 4, "medium", "todo", date(2026, 4, 21), None),
            ("Обновить контент на сайте", "Добавить 5 новых кейсов и 10 отзывов пациентов", 5, "medium", "todo", date(2026, 4, 25), meetings[2]),
            ("Согласовать план обучения", "Согласовать с главврачом план повышения квалификации", 6, "medium", "in_progress", date(2026, 4, 18), meetings[1]),
            ("Заказать оборудование для нового филиала", "Составить спецификацию и отправить запросы поставщикам", 7, "critical", "todo", date(2026, 4, 30), None),
            ("Проверить договоры с поставщиками", "Ревизия условий договоров на расходные материалы", 8, "low", "todo", date(2026, 5, 10), None),
            ("Подготовить презентацию для инвесторов", "Презентация о стратегии расширения сети", 0, "critical", "in_progress", date(2026, 4, 8), meetings[0]),
            ("Провести инвентаризацию расходников", "Полная инвентаризация по всем филиалам", 5, "medium", "todo", date(2026, 4, 3), None),
        ]
        for title, desc, user_idx, priority, status, due, mid in tasks_data:
            uid = list(users.values())[user_idx % len(users)]
            s.add(Task(id=uuid.uuid4(), tenant_id=tenant_id, title=title, description=desc,
                       assignee_id=uid, meeting_id=mid, priority=priority, status=status, due_date=due))
        await s.flush()

        # Weekly Reports
        week_start = date.today() - timedelta(days=date.today().weekday() + 7)
        week_end = week_start + timedelta(days=6)
        reports_data = [
            (1, "1. Запустила рекламу в Яндекс.Директ — CTR 3.5%\n2. Обновила лендинг — конверсия +12%\n3. Провела анализ конкурентов", "Охват: 45 000\nЛиды: 128\nCPL: 890 ₽\nROI рекламы: 340%", "Нужно утвердить бюджет на видеомаркетинг — 200 000 ₽"),
            (2, "1. Закрыл месячный отчёт — выручка 14.2 млн ₽\n2. Оптимизировал налоговую нагрузку\n3. Согласовал бюджет на Q2", "Выручка: 14.2 млн ₽ (+8%)\nМаржинальность: 42%\nФОТ: 4.8 млн ₽\nЧистая прибыль: 2.1 млн ₽", None),
            (3, "1. Провела собеседования — нанято 3 сотрудника\n2. Обновила систему мотивации\n3. Запустила адаптационную программу", "Текучесть: 8% (норма <10%)\nНовых сотрудников: 3\nЗакрытых вакансий: 5 из 7\neNPS: 72", "Прошу согласовать программу корп. обучения на 150 000 ₽"),
        ]
        for user_idx, tasks_text, metrics, requests in reports_data:
            uid = list(users.values())[user_idx]
            s.add(WeeklyReport(id=uuid.uuid4(), tenant_id=tenant_id, user_id=uid,
                               period_start=week_start, period_end=week_end,
                               completed_tasks=tasks_text, metrics_json=metrics, requests=requests,
                               status="submitted", submitted_at=datetime.now() - timedelta(hours=12)))
        await s.flush()

        # Metric Snapshots
        metrics_data = [
            ("dental_pro", "chairs_count", 24),
            ("dental_pro", "utilization_percent", 78.5),
            ("dental_pro", "avg_check", 15200),
            ("1c", "revenue_monthly", 14200000),
            ("1c", "margin_percent", 42.0),
            ("1c", "payroll_monthly", 4800000),
            ("bitrix24", "leads_count", 128),
            ("bitrix24", "lead_conversion", 32.5),
            ("bitrix24", "deals_amount", 8500000),
        ]
        for source, name, value in metrics_data:
            s.add(MetricSnapshot(id=uuid.uuid4(), tenant_id=tenant_id, source=source,
                                 metric_name=name, metric_value=value, recorded_at=now))
        await s.flush()

        # Metric Alerts
        alerts_data = [
            ("threshold", "utilization_percent: 78.5% ниже целевого порога 85%", "warning"),
            ("deviation", "avg_check: 15 200 ₽ на 8% ниже среднего за месяц (16 500 ₽)", "info"),
            ("trend", "leads_count: снижение на 15% за последние 2 недели", "warning"),
        ]
        for atype, msg, severity in alerts_data:
            s.add(MetricAlert(id=uuid.uuid4(), tenant_id=tenant_id, alert_type=atype,
                              message=msg, severity=severity))
        await s.flush()

        # Score Entries
        user_list = list(users.items())
        score_data = [
            (1, "auto_task_ontime", 5, "Настроила Яндекс.Директ кампанию в срок"),
            (1, "auto_task_ontime", 5, "Обновила лендинг в срок"),
            (1, "auto_report_ontime", 3, "Отчёт подан вовремя"),
            (1, "manual_bonus", 10, "Отличные результаты рекламной кампании"),
            (2, "auto_task_ontime", 5, "Закрыл месячный отчёт в срок"),
            (2, "auto_report_ontime", 3, "Отчёт подан вовремя"),
            (2, "auto_task_ontime", 5, "Оптимизировал налоговую нагрузку"),
            (3, "auto_task_ontime", 5, "Провела собеседования в срок"),
            (3, "auto_report_ontime", 3, "Отчёт подан вовремя"),
            (3, "auto_task_late", -3, "Просрочка по вакансии разработчика"),
            (4, "auto_task_ontime", 5, "Аудит загрузки кресел выполнен"),
            (4, "auto_task_late", -3, "Просрочка инвентаризации"),
            (5, "auto_task_ontime", 5, "Согласование плана обучения"),
            (6, "auto_task_late", -3, "Просрочка обновления HR-процессов"),
            (6, "manual_penalty", -5, "Опоздание на совещание"),
            (7, "auto_task_ontime", 5, "Подготовка документов"),
            (7, "auto_task_ontime", 5, "Проверка расчётов"),
        ]
        for user_idx, stype, pts, reason in score_data:
            name, uid = user_list[user_idx]
            s.add(ScoreEntry(id=uuid.uuid4(), tenant_id=tenant_id, user_id=uid,
                             score_type=stype, points=pts, reason=reason,
                             granted_by=list(users.values())[0] if "manual" in stype else None))
        await s.flush()

        # Peer Reviews
        s.add(PeerReview(id=uuid.uuid4(), tenant_id=tenant_id,
                         reviewer_id=user_list[1][1], reviewee_id=user_list[2][1],
                         period_start=date(2026, 3, 24), period_end=date(2026, 4, 6),
                         rating=4, comment="Хорошая работа с финансами, но коммуникация могла быть лучше"))
        s.add(PeerReview(id=uuid.uuid4(), tenant_id=tenant_id,
                         reviewer_id=user_list[2][1], reviewee_id=user_list[1][1],
                         period_start=date(2026, 3, 24), period_end=date(2026, 4, 6),
                         rating=5, comment="Отличная работа по маркетингу, результаты впечатляют"))

        await s.commit()
        print(f"Seeded tenant {tenant_id} with 10 users, 6 meetings, 10 tasks, 3 reports, 9 metrics, 3 alerts, 17 scores")


if __name__ == "__main__":
    asyncio.run(seed())
