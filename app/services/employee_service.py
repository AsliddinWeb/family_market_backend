from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.models.employee import Employee
from app.models.user import User
from app.schemas.employee import EmployeeCreate, EmployeeUpdate


async def get_employees(
    db: AsyncSession,
    page: int,
    size: int,
    branch_id: int | None,
    department_id: int | None,
    is_active: bool | None,
    search: str | None,
) -> tuple[int, list[Employee]]:
    q = (
        select(Employee)
        .join(Employee.user)
        .options(
            selectinload(Employee.user),
            selectinload(Employee.branch),
            selectinload(Employee.department),
        )
        .where(Employee.is_deleted == False, User.is_deleted == False)
    )

    if branch_id is not None:
        q = q.where(Employee.branch_id == branch_id)
    if department_id is not None:
        q = q.where(Employee.department_id == department_id)
    if is_active is not None:
        q = q.where(Employee.is_active == is_active)
    if search:
        q = q.where(User.full_name.ilike(f"%{search}%"))

    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    items = (await db.execute(q.offset((page - 1) * size).limit(size))).scalars().all()
    return total, list(items)


async def get_employee(db: AsyncSession, employee_id: int) -> Employee | None:
    result = await db.execute(
        select(Employee)
        .options(
            selectinload(Employee.user),
            selectinload(Employee.branch),
            selectinload(Employee.department),
        )
        .where(Employee.id == employee_id, Employee.is_deleted == False)
    )
    return result.scalar_one_or_none()


async def create_employee(db: AsyncSession, data: EmployeeCreate) -> Employee:
    # 1. User yaratish
    user = User(
        phone=data.phone,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    await db.flush()  # user.id ni olish uchun

    # 2. Employee yaratish
    employee = Employee(
        user_id=user.id,
        branch_id=data.branch_id,
        department_id=data.department_id,
        position=data.position,
        employment_type=data.employment_type,
        hire_date=data.hire_date,
        base_salary=data.base_salary,
        telegram_user_id=data.telegram_user_id,
        photo=data.photo,
    )
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    await db.refresh(user)
    return employee


async def update_employee(
    db: AsyncSession, employee: Employee, data: EmployeeUpdate
) -> Employee:
    employee_fields = {
        "branch_id", "department_id", "position", "employment_type",
        "hire_date", "base_salary", "telegram_user_id", "photo", "is_active"
    }
    user_fields = {"full_name", "role"}

    update_data = data.model_dump(exclude_none=True)

    for field, value in update_data.items():
        if field in employee_fields:
            setattr(employee, field, value)
        elif field in user_fields:
            setattr(employee.user, field, value)

    await db.commit()
    await db.refresh(employee)
    return employee


async def delete_employee(db: AsyncSession, employee: Employee) -> None:
    employee.is_deleted = True
    employee.is_active = False
    employee.user.is_active = False
    await db.commit()