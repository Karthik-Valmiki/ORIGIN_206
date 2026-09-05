"""
Admin-only routes:
  - List/create users (officers)
  - List product categories
  - List all inspections (dashboard view)
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_db, require_role
from app.core.security import get_password_hash
from app.models.user import User, Role
from app.models.inspection import Inspection, ProductCategory
from app.schemas.auth import UserCreate, UserOut
from app.schemas.inspection import InspectionOut, CategoryOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("ADMIN")),
):
    result = await db.execute(
        select(User).options(selectinload(User.roles)).order_by(User.created_at.desc())
    )
    return result.scalars().all()


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_officer(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("ADMIN")),
):
    """Admin creates a new officer account — no self-registration for officers."""
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered.")

    role_result = await db.execute(
        select(Role).where(Role.role_name == user_data.role_name)
    )
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail=f"Role '{user_data.role_name}' not found.")

    new_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        roles=[role],
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user, ["roles"])
    return new_user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_role("ADMIN")),
):
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself.")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_active = False
    await db.commit()


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("ADMIN", "OFFICER")),
):
    result = await db.execute(select(ProductCategory).order_by(ProductCategory.category_name))
    return result.scalars().all()


@router.get("/inspections", response_model=list[InspectionOut])
async def list_all_inspections(
    status_filter: str | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("ADMIN")),
):
    """Admin dashboard — paginated list of all inspections with optional status filter."""
    q = select(Inspection).options(selectinload(Inspection.product_category))
    if status_filter:
        q = q.where(Inspection.status == status_filter.upper())
    q = q.order_by(Inspection.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()
