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
    """Admin creates a new user account (officer or admin)."""
    normalized_email = user_data.email.lower().strip()
    result = await db.execute(
        select(User).where(func.lower(User.email) == normalized_email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered.")

    normalized_role = user_data.role_name.upper().strip()
    role_result = await db.execute(
        select(Role).where(Role.role_name == normalized_role)
    )
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail=f"Role '{normalized_role}' not found.")

    new_user = User(
        full_name=user_data.full_name.strip(),
        email=normalized_email,
        password_hash=get_password_hash(user_data.password),
        roles=[role],
    )
    db.add(new_user)
    await db.commit()

    res = await db.execute(
        select(User).where(User.id == new_user.id).options(selectinload(User.roles))
    )
    return res.scalar_one()


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_role("ADMIN")),
):
    """Deactivate a user account. Prevents deactivating self or the last active admin."""
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself.")

    user_res = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.roles))
    )
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Guard: prevent removing the last active administrator
    if "ADMIN" in {r.role_name.upper() for r in user.roles}:
        admin_count_res = await db.execute(
            select(func.count(User.id))
            .join(User.roles)
            .where(Role.role_name == "ADMIN", User.is_active.is_(True))
        )
        if (admin_count_res.scalar() or 0) <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot deactivate the only active system administrator.",
            )

    user.is_active = False
    await db.commit()


@router.patch("/users/{user_id}/activate", response_model=UserOut)
async def activate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("ADMIN")),
):
    """Reactivate a previously deactivated user account."""
    user_res = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.roles))
    )
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = True
    await db.commit()

    res = await db.execute(
        select(User).where(User.id == user.id).options(selectinload(User.roles))
    )
    return res.scalar_one()


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
