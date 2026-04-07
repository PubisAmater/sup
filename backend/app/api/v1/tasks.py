"""CRUD-операции для задач и фильтр по просроченным.

Модуль управляет жизненным циклом задач: создание (вручную или из AI-анализа
совещаний), просмотр с фильтрацией, обновление статуса и удаление.
Задачи привязываются к исполнителю (``assignee_id``), могут быть связаны
с совещанием и решением. Отдельный эндпоинт ``/overdue`` возвращает
просроченные задачи для контроля CEO.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=list[TaskRead])
async def list_tasks(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    assignee_id: uuid.UUID | None = None,
    meeting_id: uuid.UUID | None = None,
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = None,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Возвращает список задач с пагинацией и множественной фильтрацией.

    Поддерживает фильтры по исполнителю, совещанию, статусу и приоритету.
    Результаты отсортированы по дате создания (новые сверху).
    Используется на странице «Задачи» и в карточке совещания.

    Args:
        offset: Смещение для пагинации.
        limit: Максимум записей (1-100).
        assignee_id: Фильтр по UUID исполнителя.
        meeting_id: Фильтр по UUID совещания-источника.
        status_filter: Фильтр по статусу (``todo``, ``in_progress``, ``done``).
        priority: Фильтр по приоритету (``low``, ``medium``, ``high``, ``critical``).
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        list[TaskRead]: Список задач, соответствующих критериям.
    """
    query = select(Task)
    if assignee_id:
        query = query.where(Task.assignee_id == assignee_id)
    if meeting_id:
        query = query.where(Task.meeting_id == meeting_id)
    if status_filter:
        query = query.where(Task.status == status_filter)
    if priority:
        query = query.where(Task.priority == priority)
    query = query.order_by(Task.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/overdue", response_model=list[TaskRead])
async def list_overdue_tasks(
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Возвращает список просроченных незавершённых задач.

    Выбирает задачи с ``due_date`` раньше сегодняшней даты и статусом
    ``todo`` или ``in_progress``. Отсортированы по дедлайну (самые старые
    сверху). Используется CEO для быстрого выявления проблемных зон
    и отображается как алерт на дашборде.

    Args:
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        list[TaskRead]: Просроченные задачи, отсортированные по дедлайну.
    """
    from datetime import date
    today = date.today()
    result = await session.execute(
        select(Task)
        .where(Task.due_date < today)
        .where(Task.status.in_(["todo", "in_progress"]))
        .order_by(Task.due_date.asc())
    )
    return result.scalars().all()


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Возвращает данные конкретной задачи по UUID.

    Args:
        task_id: UUID задачи.
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        TaskRead: Полные данные задачи.

    Raises:
        HTTPException: 404, если задача не найдена.
    """
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.post("/", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Создаёт новую задачу в системе.

    Задача привязывается к тенанту текущего пользователя. Может быть связана
    с совещанием и/или решением. Создание задач вручную дополняет автоматическое
    создание из AI-анализа совещаний.

    Args:
        data: Данные задачи (название, описание, исполнитель, приоритет, дедлайн).
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        TaskRead: Созданная задача с присвоенным UUID.
    """
    task = Task(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(current_user["tenant_id"]),
        **data.model_dump(),
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: uuid.UUID,
    data: TaskUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Частично обновляет задачу (PATCH-семантика).

    Позволяет изменить статус, приоритет, исполнителя, дедлайн и т.д.
    Типичное использование — перевод задачи в статус ``done`` при завершении.
    Обновляются только переданные поля.

    Args:
        task_id: UUID обновляемой задачи.
        data: Поля для обновления.
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        TaskRead: Обновлённые данные задачи.

    Raises:
        HTTPException: 404, если задача не найдена.
    """
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    await session.commit()
    await session.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Удаляет задачу из системы.

    Args:
        task_id: UUID удаляемой задачи.
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Raises:
        HTTPException: 404, если задача не найдена.
    """
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    await session.delete(task)
    await session.commit()
