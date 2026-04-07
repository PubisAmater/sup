"""CRUD-операции для управления сотрудниками клиники.

Модуль обеспечивает полный жизненный цикл записей сотрудников: создание,
просмотр (с пагинацией и фильтрацией по отделу), обновление и удаление.
Сотрудники привязаны к тенанту (клинике) через ``tenant_id``, что позволяет
работать в мультитенантном режиме. Данные используются в дашборде, при
назначении задач и формировании отчётов.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeRead, EmployeeUpdate

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("/", response_model=list[EmployeeRead])
async def list_employees(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    department: str | None = None,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Возвращает список сотрудников с пагинацией и фильтрацией по отделу.

    Используется на странице «Сотрудники» и в выпадающих списках при назначении
    задач. Поддерживает параметры ``offset``/``limit`` для постраничного вывода
    и необязательный фильтр ``department`` (например, «терапия», «хирургия»).

    Args:
        offset: Смещение для пагинации (по умолчанию 0).
        limit: Максимальное количество записей (1-100, по умолчанию 20).
        department: Фильтр по названию отдела (необязательный).
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        list[EmployeeRead]: Список сотрудников, соответствующих критериям.
    """
    query = select(Employee)
    if department:
        query = query.where(Employee.department == department)
    query = query.offset(offset).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{employee_id}", response_model=EmployeeRead)
async def get_employee(
    employee_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Возвращает данные конкретного сотрудника по его UUID.

    Используется для отображения профиля сотрудника и при редактировании
    его карточки. Возвращает 404, если сотрудник не найден.

    Args:
        employee_id: UUID сотрудника.
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        EmployeeRead: Полные данные сотрудника.

    Raises:
        HTTPException: 404, если сотрудник с указанным ID не существует.
    """
    result = await session.execute(select(Employee).where(Employee.id == employee_id))
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return employee


@router.post("/", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
async def create_employee(
    data: EmployeeCreate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Создаёт нового сотрудника в системе.

    Привязывает сотрудника к тенанту текущего пользователя. Используется при
    найме нового работника — запись появляется в списке сотрудников и становится
    доступна для назначения задач и включения в совещания.

    Args:
        data: Данные для создания сотрудника (должность, отдел и т.д.).
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        EmployeeRead: Созданная запись сотрудника с присвоенным UUID.
    """
    employee = Employee(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(current_user["tenant_id"]),
        **data.model_dump(),
    )
    session.add(employee)
    await session.commit()
    await session.refresh(employee)
    return employee


@router.patch("/{employee_id}", response_model=EmployeeRead)
async def update_employee(
    employee_id: uuid.UUID,
    data: EmployeeUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Частично обновляет данные сотрудника (PATCH-семантика).

    Обновляет только переданные поля — остальные остаются без изменений.
    Используется для изменения должности, отдела или деактивации сотрудника.

    Args:
        employee_id: UUID сотрудника для обновления.
        data: Поля для обновления (только те, что переданы клиентом).
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        EmployeeRead: Обновлённые данные сотрудника.

    Raises:
        HTTPException: 404, если сотрудник не найден.
    """
    result = await session.execute(select(Employee).where(Employee.id == employee_id))
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)

    await session.commit()
    await session.refresh(employee)
    return employee


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Удаляет сотрудника из системы.

    Полностью удаляет запись из БД. Используется при увольнении сотрудника.
    В продакшене рекомендуется использовать мягкое удаление (``is_active=False``)
    через PATCH-эндпоинт, чтобы сохранить историю.

    Args:
        employee_id: UUID удаляемого сотрудника.
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Raises:
        HTTPException: 404, если сотрудник не найден.
    """
    result = await session.execute(select(Employee).where(Employee.id == employee_id))
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    await session.delete(employee)
    await session.commit()
