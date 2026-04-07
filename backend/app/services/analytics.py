"""
Сервис аналитики и мониторинга бизнес-метрик с обнаружением отклонений.

ЧТО: Модуль предоставляет класс AnalyticsService для проверки бизнес-метрик
на отклонения от пороговых значений и исторических средних, а также для расчёта
формулы выручки стоматологической клиники.

ЗАЧЕМ: Автоматический мониторинг ключевых показателей позволяет руководителю
оперативно реагировать на негативные тенденции, не дожидаясь ежемесячных отчётов.
Система генерирует алерты (MetricAlert) при обнаружении отклонений, которые
затем могут отправляться в Telegram.

КАК: Используется два механизма обнаружения отклонений:

  1. Абсолютные пороги (threshold) --- метрика сравнивается с заданным мин/макс:
     - utilization_percent: min=70, max=100, severity=warning
       Загрузка кресел не должна опускаться ниже 70%. Ниже --- проблемы с записью.
     - lead_conversion: min=20, severity=info
       Конверсия лидов не должна быть ниже 20%. Ниже --- проблемы с маркетингом.

  2. Отклонение от среднего (deviation) --- текущее значение сравнивается со средним
     за предыдущие 30 дней (исключая последнюю неделю, чтобы избежать self-reference):
     - Если отклонение > 20% --- алерт уровня info.
     - Если отклонение > 30% --- алерт уровня warning.
     - avg_check: min_deviation_pct=15 --- специфичный порог для среднего чека
       (записан в THRESHOLDS, но в check_deviations используется общий порог 20%).
     - revenue_monthly: min_deviation_pct=10 --- специфичный порог для выручки,
       severity=critical (записан в THRESHOLDS для возможного расширения).

  Формула отклонения: deviation_pct = |current - avg| / avg * 100%

Формула выручки (get_revenue_formula):
  Фактическая выручка = Кресла x (Загрузка / 100) x Средний_чек x 22 x 8
  Где:
    - Кресла --- количество стоматологических кресел (из Dental Pro).
    - Загрузка --- процент загрузки кресел (из Dental Pro).
    - Средний_чек --- средняя стоимость приёма (из Dental Pro).
    - 22 --- количество рабочих дней в месяце.
    - 8 --- количество рабочих часов в день.

  Целевая выручка = Кресла x 3 000 000 руб.
  (Норматив: 3 млн руб./мес на одно стоматологическое кресло.)

  gap_percent = (1 - Фактическая / Целевая) x 100%
  Показывает, на сколько процентов фактическая выручка отстаёт от целевой.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metric_alert import MetricAlert
from app.models.metric_snapshot import MetricSnapshot

logger = logging.getLogger(__name__)

# Пороговые значения для алертов.
#
# Структура каждого элемента:
#   - "min" / "max": абсолютные пороги. Если текущее значение выходит за них --- алерт.
#   - "min_deviation_pct": минимальный процент отклонения от среднего для алерта
#     (используется как справочник; в check_deviations применяется общий порог 20%).
#   - "severity": уровень серьёзности алерта ("info", "warning", "critical").
#
# "utilization_percent" --- загрузка кресел: алерт warning если < 70%.
# "avg_check" --- средний чек: алерт warning при отклонении > 15% от среднего.
# "revenue_monthly" --- месячная выручка: алерт critical при отклонении > 10%.
# "lead_conversion" --- конверсия лидов: алерт info если < 20%.
THRESHOLDS = {
    "utilization_percent": {"min": 70, "max": 100, "severity": "warning"},
    "avg_check": {"min_deviation_pct": 15, "severity": "warning"},
    "revenue_monthly": {"min_deviation_pct": 10, "severity": "critical"},
    "lead_conversion": {"min": 20, "severity": "info"},
}


class AnalyticsService:
    """
    Сервис мониторинга и обнаружения отклонений в бизнес-метриках.

    ЧТО: Предоставляет два основных метода:
      - check_deviations() --- проверяет текущие метрики на отклонения и создаёт алерты.
      - get_revenue_formula() --- рассчитывает формулу выручки и gap до целевой.

    ЗАЧЕМ: Автоматический мониторинг метрик заменяет ручной анализ отчётов.
    Руководитель получает только алерты о проблемах, а не тонны данных.

    КАК: Все метрики хранятся в таблице MetricSnapshot (metric_name, metric_value,
    recorded_at, tenant_id). Алерты сохраняются в MetricAlert. Работает с
    асинхронной сессией SQLAlchemy.
    """

    async def check_deviations(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> list[MetricAlert]:
        """
        Проверяет текущие метрики на отклонения от порогов и исторических средних.

        ЧТО: Загружает снимки метрик за последнюю неделю, сравнивает их с абсолютными
        порогами (THRESHOLDS) и средними значениями за предыдущие 30 дней. При
        обнаружении отклонений создаёт объекты MetricAlert и сохраняет их в БД.

        ЗАЧЕМ: Это основной метод мониторинга --- он запускается периодически
        (по расписанию) и генерирует алерты, которые затем отправляются
        руководителю через Telegram.

        КАК работает алгоритм обнаружения отклонений:
          1. Загружает все MetricSnapshot за последние 7 дней для данного tenant_id.
          2. Группирует снимки по metric_name.
          3. Для каждой метрики берёт самое свежее значение (current_value).
          4. Проверка абсолютных порогов:
             - Если метрика есть в THRESHOLDS и current_value < threshold["min"],
               создаётся алерт типа "threshold" с severity из THRESHOLDS.
          5. Проверка отклонения от среднего:
             - Рассчитывает среднее значение метрики за 30 дней ИСКЛЮЧАЯ последнюю
               неделю (чтобы текущий всплеск не влиял на базовую линию).
             - Формула: deviation_pct = |current - avg| / avg * 100%.
             - Если deviation_pct > 20% --- алерт типа "deviation".
             - Severity: "warning" если отклонение > 30%, иначе "info".
          6. Все алерты сохраняются в БД через session.add() + session.commit().

        Аргументы:
            session (AsyncSession): Асинхронная сессия SQLAlchemy для работы с БД.
            tenant_id (uuid.UUID): Идентификатор тенанта (клиники).

        Возвращает:
            list[MetricAlert]: Список созданных алертов. Пустой список, если
            отклонений не обнаружено.
        """
        alerts = []
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)

        # Get latest snapshots per metric
        latest_result = await session.execute(
            select(MetricSnapshot)
            .where(MetricSnapshot.tenant_id == tenant_id)
            .where(MetricSnapshot.recorded_at >= week_ago)
            .order_by(MetricSnapshot.recorded_at.desc())
        )
        latest_snapshots = latest_result.scalars().all()

        # Group by metric_name
        by_name: dict[str, list[MetricSnapshot]] = {}
        for s in latest_snapshots:
            by_name.setdefault(s.metric_name, []).append(s)

        for metric_name, snapshots in by_name.items():
            if not snapshots:
                continue

            current_value = snapshots[0].metric_value

            # Check absolute thresholds
            threshold = THRESHOLDS.get(metric_name)
            if threshold:
                if "min" in threshold and current_value < threshold["min"]:
                    alert = MetricAlert(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        metric_snapshot_id=snapshots[0].id,
                        alert_type="threshold",
                        message=f"{metric_name}: {current_value:.1f} ниже порога {threshold['min']}",
                        severity=threshold.get("severity", "info"),
                    )
                    alerts.append(alert)

            # Check deviation from average (last 30 days)
            month_ago = now - timedelta(days=30)
            avg_result = await session.execute(
                select(func.avg(MetricSnapshot.metric_value))
                .where(MetricSnapshot.tenant_id == tenant_id)
                .where(MetricSnapshot.metric_name == metric_name)
                .where(MetricSnapshot.recorded_at >= month_ago)
                .where(MetricSnapshot.recorded_at < week_ago)
            )
            avg_value = avg_result.scalar()

            if avg_value and avg_value > 0:
                deviation_pct = abs(current_value - avg_value) / avg_value * 100
                if deviation_pct > 20:
                    direction = "выше" if current_value > avg_value else "ниже"
                    alert = MetricAlert(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        metric_snapshot_id=snapshots[0].id,
                        alert_type="deviation",
                        message=f"{metric_name}: {current_value:.1f} на {deviation_pct:.0f}% {direction} среднего ({avg_value:.1f})",
                        severity="warning" if deviation_pct > 30 else "info",
                    )
                    alerts.append(alert)

        # Persist alerts
        for alert in alerts:
            session.add(alert)
        if alerts:
            await session.commit()

        return alerts

    async def get_revenue_formula(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict:
        """
        Рассчитывает формулу выручки стоматологической клиники.

        ЧТО: Получает последние значения ключевых метрик (кресла, загрузка,
        средний чек), рассчитывает фактическую и целевую выручку, определяет
        процент отставания (gap).

        ЗАЧЕМ: Формула выручки --- это ключевой управленческий инструмент для
        руководителя клиники. Она показывает:
          - Какие параметры влияют на выручку и в какой степени.
          - Где находится основная точка роста (больше кресел? выше загрузка? дороже чек?).
          - Насколько далеко фактическая выручка от целевой.

        КАК работает расчёт:
          1. Получает последние снимки метрик из MetricSnapshot:
             - "chairs_count" --- количество стоматологических кресел.
             - "utilization_percent" --- процент загрузки кресел.
             - "avg_check" --- средний чек одного приёма (руб.).
          2. Рассчитывает фактическую выручку:
             actual_revenue = chairs * (utilization / 100) * avg_check * 22 * 8
             Где 22 --- рабочих дней в месяце, 8 --- рабочих часов в день.
             Это означает: сколько кресел работает x долю занятости x стоимость
             одного часа x количество рабочих часов в месяце.
          3. Рассчитывает целевую выручку:
             target_revenue = chairs * 3 000 000 руб.
             Норматив стоматологической отрасли: 3 млн руб./мес на одно кресло.
          4. Рассчитывает gap_percent:
             gap = (1 - actual / target) * 100%
             Положительное значение --- отставание от цели.
             Отрицательное --- перевыполнение.

        Аргументы:
            session (AsyncSession): Асинхронная сессия SQLAlchemy для работы с БД.
            tenant_id (uuid.UUID): Идентификатор тенанта (клиники).

        Возвращает:
            dict: Словарь с компонентами формулы:
                - "chairs" (int): Количество кресел.
                - "utilization_percent" (float): Загрузка в процентах.
                - "avg_check" (float): Средний чек в рублях.
                - "revenue" (float): Расчётная фактическая выручка (руб./мес).
                - "target_revenue" (float): Целевая выручка (руб./мес).
                - "gap_percent" (float): Процент отставания от целевой выручки.
        """
        now = datetime.now(timezone.utc)
        month_ago = now - timedelta(days=30)

        async def _latest_metric(name: str) -> float:
            result = await session.execute(
                select(MetricSnapshot.metric_value)
                .where(MetricSnapshot.tenant_id == tenant_id)
                .where(MetricSnapshot.metric_name == name)
                .order_by(MetricSnapshot.recorded_at.desc())
                .limit(1)
            )
            return result.scalar() or 0.0

        chairs = await _latest_metric("chairs_count")
        utilization = await _latest_metric("utilization_percent")
        avg_check = await _latest_metric("avg_check")

        # Норма: стоматологическое кресло 3 млн ₽/мес
        target_per_chair = 3_000_000
        target_revenue = chairs * target_per_chair
        actual_revenue = chairs * (utilization / 100) * avg_check * 22 * 8  # рабочих дней * часов

        return {
            "chairs": int(chairs),
            "utilization_percent": round(utilization, 1),
            "avg_check": round(avg_check, 0),
            "revenue": round(actual_revenue, 0),
            "target_revenue": round(target_revenue, 0),
            "gap_percent": round((1 - actual_revenue / target_revenue) * 100, 1) if target_revenue > 0 else 0,
        }
