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
from app.models.inspection import Inspection, ProductCategory, RuleSet, RuleVersion, Rule
from app.schemas.auth import UserCreate, UserOut
from app.schemas.inspection import (
    InspectionOut, CategoryOut,
    RuleOut, RuleCreate, RuleUpdate, RuleVersionOut, RuleVersionCreate
)

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


@router.patch("/users/{user_id}/deactivate", response_model=UserOut)
async def deactivate_user_patch(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_role("ADMIN")),
):
    """Deactivate a user account via PATCH."""
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself.")

    user_res = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.roles))
    )
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

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

    res = await db.execute(
        select(User).where(User.id == user.id).options(selectinload(User.roles))
    )
    return res.scalar_one()


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


# ══════════════════════════════════════════════════════════════════════════════
#  LMPC RULES MANAGEMENT (ADMIN ONLY)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/rules", response_model=RuleVersionOut)
async def get_active_rules(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("ADMIN")),
):
    """Returns the currently active rule version and all its configured LMPC rules."""
    result = await db.execute(
        select(RuleVersion)
        .where(RuleVersion.is_active.is_(True))
        .options(selectinload(RuleVersion.rules))
        .order_by(RuleVersion.effective_from.desc())
        .limit(1)
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="No active rule version found.")
    return version


@router.post("/rules", response_model=RuleOut, status_code=status.HTTP_201_CREATED)
async def create_rule(
    rule_in: RuleCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("ADMIN")),
):
    """Admin creates a new rule under the currently active rule version."""
    result = await db.execute(
        select(RuleVersion)
        .where(RuleVersion.is_active.is_(True))
        .order_by(RuleVersion.effective_from.desc())
        .limit(1)
    )
    active_ver = result.scalar_one_or_none()
    if not active_ver:
        raise HTTPException(status_code=400, detail="No active rule version found.")

    code = rule_in.rule_code.upper().strip()
    existing = await db.execute(
        select(Rule).where(
            Rule.rule_version_id == active_ver.id,
            Rule.rule_code == code,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Rule code '{code}' already exists in active version.",
        )

    # Validate check_type against allowed database constraint
    valid_checks = {"PRESENCE", "VALUE", "FORMAT", "UNIT", "PLACEMENT", "LEGIBILITY", "VISUAL", "DECLARATION"}
    check_type_norm = rule_in.check_type.upper().strip()
    if check_type_norm not in valid_checks:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid check_type '{check_type_norm}'. Allowed: {sorted(valid_checks)}",
        )

    params = {
        "is_mandatory": rule_in.is_mandatory,
        "field": rule_in.field.upper().strip() if rule_in.field else None,
        "rule_ref": rule_in.rule_ref.strip() if rule_in.rule_ref else None,
    }

    new_rule = Rule(
        rule_version_id=active_ver.id,
        rule_code=code,
        check_type=check_type_norm,
        description=rule_in.description.strip() if rule_in.description else None,
        parameters=params,
    )
    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)
    return new_rule


@router.put("/rules/{rule_id}", response_model=RuleOut)
async def update_rule(
    rule_id: uuid.UUID,
    rule_in: RuleUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("ADMIN")),
):
    """Admin updates rule parameters, check type, or toggles mandatory compliance status."""
    rule = await db.get(Rule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found.")

    if rule_in.check_type is not None:
        valid_checks = {"PRESENCE", "VALUE", "FORMAT", "UNIT", "PLACEMENT", "LEGIBILITY", "VISUAL", "DECLARATION"}
        ct = rule_in.check_type.upper().strip()
        if ct not in valid_checks:
            raise HTTPException(status_code=422, detail=f"Invalid check_type. Allowed: {sorted(valid_checks)}")
        rule.check_type = ct

    if rule_in.description is not None:
        rule.description = rule_in.description.strip()

    params = dict(rule.parameters or {})
    if rule_in.is_mandatory is not None:
        params["is_mandatory"] = rule_in.is_mandatory
    if rule_in.field is not None:
        params["field"] = rule_in.field.upper().strip() if rule_in.field else None
    if rule_in.rule_ref is not None:
        params["rule_ref"] = rule_in.rule_ref.strip() if rule_in.rule_ref else None
    rule.parameters = params

    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("ADMIN")),
):
    """Admin deletes a rule from the active version."""
    rule = await db.get(Rule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found.")
    await db.delete(rule)
    await db.commit()


@router.post("/rules/version", response_model=RuleVersionOut, status_code=status.HTTP_201_CREATED)
async def create_rule_version(
    ver_in: RuleVersionCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("ADMIN")),
):
    """
    Publishes and activates a new LMPC rule version.
    Deactivates older versions and optionally clones rules from the previous active version.
    """
    res = await db.execute(select(RuleSet).limit(1))
    ruleset = res.scalar_one_or_none()
    if not ruleset:
        ruleset = RuleSet(
            name="LMPC 2011 Standard",
            description="Legal Metrology (Packaged Commodities) Rules, 2011",
        )
        db.add(ruleset)
        await db.commit()
        await db.refresh(ruleset)

    # Find previous active version
    prev_active_res = await db.execute(
        select(RuleVersion)
        .where(RuleVersion.rule_set_id == ruleset.id, RuleVersion.is_active.is_(True))
        .options(selectinload(RuleVersion.rules))
        .order_by(RuleVersion.effective_from.desc())
        .limit(1)
    )
    prev_ver = prev_active_res.scalar_one_or_none()

    # Deactivate previous versions
    all_vers = await db.execute(select(RuleVersion).where(RuleVersion.rule_set_id == ruleset.id))
    for v in all_vers.scalars().all():
        v.is_active = False

    new_ver = RuleVersion(
        rule_set_id=ruleset.id,
        version_number=ver_in.version_number.strip(),
        is_active=True,
    )
    db.add(new_ver)
    await db.commit()
    await db.refresh(new_ver)

    # Clone rules if requested
    if ver_in.clone_from_active and prev_ver:
        for old_r in prev_ver.rules:
            db.add(Rule(
                rule_version_id=new_ver.id,
                rule_code=old_r.rule_code,
                check_type=old_r.check_type,
                description=old_r.description,
                parameters=dict(old_r.parameters or {}),
            ))
        await db.commit()

    res = await db.execute(
        select(RuleVersion)
        .where(RuleVersion.id == new_ver.id)
        .options(selectinload(RuleVersion.rules))
    )
    return res.scalar_one()
