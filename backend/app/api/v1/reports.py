"""Еженедельные отчёты сотрудников: CRUD, подача и доставка CEO.

Модуль обеспечивает полный цикл еженедельной отчётности:
- Создание черновика отчёта за период (неделю);
- Редактирование до подачи (заполнение выполненных задач, метрик, запросов);
- Подача отчёта (``submit``) — фиксирует время и ставит в очередь доставку
  CEO через Telegram + генерацию аудио-саммари через SpeechKit;
- Получение отчёта текущей недели для быстрого доступа.

CEO получает отчёты автоматически в Telegram-бот после подачи сотрудником.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.weekly_report import WeeklyReport
from app.schemas.weekly_report import ReportCreate, ReportRead, ReportUpdate

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/", response_model=list[ReportRead])
async def list_reports(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user_id: uuid.UUID | None = None,
    status_filter: str | None = Query(None, alias="status"),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Возвращает список еженедельных отчётов с пагинацией и фильтрацией.

    Позволяет CEO просматривать все отчёты или фильтровать по конкретному
    сотруднику и статусу (``draft``, ``submitted``). Результаты отсортированы
    по дате окончания периода (новые сверху).

    Args:
        offset: Смещение для пагинации.
        limit: Максимум записей (1-100).
        user_id: Фильтр по UUID автора отчёта.
        status_filter: Фильтр по статусу отчёта.
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        list[ReportRead]: Список отчётов.
    """
    query = select(WeeklyReport)
    if user_id:
        query = query.where(WeeklyReport.user_id == user_id)
    if status_filter:
        query = query.where(WeeklyReport.status == status_filter)
    query = query.order_by(WeeklyReport.period_end.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/current-week", response_model=ReportRead | None)
async def get_current_week_report(
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Возвращает отчёт текущего пользователя за текущую неделю.

    Автоматически вычисляет границы текущей недели (понедельник-воскресенье)
    и ищет отчёт для текущего пользователя. Возвращает ``null``, если
    отчёт ещё не создан. Используется фронтендом для отображения формы
    заполнения еженедельного отчёта.

    Args:
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        ReportRead | None: Отчёт текущей недели или ``null``.
    """
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    result = await session.execute(
        select(WeeklyReport)
        .where(WeeklyReport.user_id == uuid.UUID(current_user["sub"]))
        .where(WeeklyReport.period_start == week_start)
        .where(WeeklyReport.period_end == week_end)
    )
    return result.scalar_one_or_none()


@router.get("/{report_id}", response_model=ReportRead)
async def get_report(
    report_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Возвращает конкретный отчёт по UUID.

    Args:
        report_id: UUID отчёта.
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        ReportRead: Данные отчёта.

    Raises:
        HTTPException: 404, если отчёт не найден.
    """
    result = await session.execute(select(WeeklyReport).where(WeeklyReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


@router.post("/", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
async def create_report(
    data: ReportCreate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Создаёт черновик еженедельного отчёта.

    Привязывает отчёт к текущему пользователю и его тенанту.
    После создания отчёт имеет статус ``draft`` и может быть
    дополнен через PATCH до момента подачи (``submit``).

    Args:
        data: Период отчёта и содержание (задачи, метрики, запросы).
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        ReportRead: Созданный отчёт-черновик.
    """
    report = WeeklyReport(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(current_user["tenant_id"]),
        user_id=uuid.UUID(current_user["sub"]),
        **data.model_dump(),
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


@router.patch("/{report_id}", response_model=ReportRead)
async def update_report(
    report_id: uuid.UUID,
    data: ReportUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Обновляет черновик отчёта (PATCH-семантика).

    Позволяет дополнить или изменить содержание отчёта до подачи.
    Обновляются только переданные поля.

    Args:
        report_id: UUID обновляемого отчёта.
        data: Поля для обновления.
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        ReportRead: Обновлённый отчёт.

    Raises:
        HTTPException: 404, если отчёт не найден.
    """
    result = await session.execute(select(WeeklyReport).where(WeeklyReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(report, field, value)

    await session.commit()
    await session.refresh(report)
    return report


@router.post("/{report_id}/submit", response_model=ReportRead)
async def submit_report(
    report_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await session.execute(select(WeeklyReport).where(WeeklyReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    report.status = "submitted"
    report.submitted_at = datetime.now(timezone.utc)
    await session.commit()

    # Enqueue delivery to CEO
    try:
        from arq.connections import create_pool
        from app.config import get_settings
        pool = await create_pool(get_settings().redis_url)
        await pool.enqueue_job("deliver_report_to_ceo", str(report_id))
        await pool.enqueue_job("generate_audio_summary", str(report_id))
    except Exception:
        pass

    await session.refresh(report)
    return report
