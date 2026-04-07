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
    result = await session.execute(select(Employee).where(Employee.id == employee_id))
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    await session.delete(employee)
    await session.commit()
