from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.branch import Branch, Department
from app.schemas.branch import BranchCreate, BranchUpdate, DepartmentCreate, DepartmentUpdate


# ── Branch ───────────────────────────────────────────────────

async def get_branches(
    db: AsyncSession,
    page: int,
    size: int,
    is_active: bool | None,
    search: str | None,
) -> tuple[int, list[Branch]]:
    q = select(Branch).where(Branch.is_deleted == False)

    if is_active is not None:
        q = q.where(Branch.is_active == is_active)
    if search:
        q = q.where(Branch.name.ilike(f"%{search}%"))

    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    items = (await db.execute(q.offset((page - 1) * size).limit(size))).scalars().all()
    return total, list(items)


async def get_branch(db: AsyncSession, branch_id: int) -> Branch | None:
    return await db.scalar(
        select(Branch).where(Branch.id == branch_id, Branch.is_deleted == False)
    )


async def create_branch(db: AsyncSession, data: BranchCreate) -> Branch:
    branch = Branch(**data.model_dump())
    db.add(branch)
    await db.commit()
    await db.refresh(branch)
    return branch


async def update_branch(db: AsyncSession, branch: Branch, data: BranchUpdate) -> Branch:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(branch, field, value)
    await db.commit()
    await db.refresh(branch)
    return branch


async def delete_branch(db: AsyncSession, branch: Branch) -> None:
    branch.is_deleted = True
    branch.is_active = False
    await db.commit()


# ── Department ───────────────────────────────────────────────

async def get_departments(
    db: AsyncSession,
    page: int,
    size: int,
    branch_id: int | None,
    is_active: bool | None,
    search: str | None,
) -> tuple[int, list[Department]]:
    q = select(Department)

    if branch_id is not None:
        q = q.where(Department.branch_id == branch_id)
    if is_active is not None:
        q = q.where(Department.is_active == is_active)
    if search:
        q = q.where(Department.name.ilike(f"%{search}%"))

    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    items = (await db.execute(q.offset((page - 1) * size).limit(size))).scalars().all()
    return total, list(items)


async def get_department(db: AsyncSession, dept_id: int) -> Department | None:
    return await db.scalar(select(Department).where(Department.id == dept_id))


async def create_department(db: AsyncSession, data: DepartmentCreate) -> Department:
    dept = Department(**data.model_dump())
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return dept


async def update_department(
    db: AsyncSession, dept: Department, data: DepartmentUpdate
) -> Department:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(dept, field, value)
    await db.commit()
    await db.refresh(dept)
    return dept


async def delete_department(db: AsyncSession, dept: Department) -> None:
    dept.is_active = False
    await db.commit()