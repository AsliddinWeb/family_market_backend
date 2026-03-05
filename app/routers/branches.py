from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_admin, get_current_user, get_hr
from app.models.user import User
from app.schemas.branch import (
    BranchCreate, BranchOut, BranchUpdate,
    PaginatedBranches,
)
from app.services import branch_service

router = APIRouter(prefix="/api/branches", tags=["Branches"])


@router.get("", response_model=PaginatedBranches)
async def list_branches(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    is_active: bool | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    total, items = await branch_service.get_branches(db, page, size, is_active, search)
    return PaginatedBranches(total=total, page=page, size=size, items=items)


@router.post("", response_model=BranchOut, status_code=201)
async def create_branch(
    data: BranchCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin),
):
    return await branch_service.create_branch(db, data)


@router.get("/{branch_id}", response_model=BranchOut)
async def get_branch(
    branch_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    branch = await branch_service.get_branch(db, branch_id)
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return branch


@router.patch("/{branch_id}", response_model=BranchOut)
async def update_branch(
    branch_id: int,
    data: BranchUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin),
):
    branch = await branch_service.get_branch(db, branch_id)
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return await branch_service.update_branch(db, branch, data)


@router.delete("/{branch_id}", status_code=204)
async def delete_branch(
    branch_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin),
):
    branch = await branch_service.get_branch(db, branch_id)
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    await branch_service.delete_branch(db, branch)