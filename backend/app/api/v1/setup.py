from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.core.deps import get_db
from app.core.security import get_password_hash
from app.models.user import User, Role
from app.models.inspection import ProductCategory, RuleSet, RuleVersion
from app.schemas.setup import SetupRequest

router = APIRouter(prefix="/setup", tags=["setup"])

_SETUP_LOCK_KEY = 987654321


@router.get("/status")
async def setup_status(db: AsyncSession = Depends(get_db)):
    """Used by the frontend to check if onboarding is needed."""
    result = await db.execute(select(User).limit(1))
    initialized = result.scalar_one_or_none() is not None
    return {"initialized": initialized}


@router.post("/init", status_code=status.HTTP_201_CREATED)
async def initialize_system(
    req: SetupRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    One-time system bootstrap.
    - Advisory lock prevents simultaneous calls.
    - Idempotent: 403 if already initialized.
    - Uses separate DB operations per step so a partial failure rolls back cleanly.
    """
    # ── 1. Advisory lock (non-blocking) ──────────────────────────────────────
    acquired = await db.execute(
        text("SELECT pg_try_advisory_lock(:key)"), {"key": _SETUP_LOCK_KEY}
    )
    if not acquired.scalar():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Setup already in progress. Retry in a moment.",
        )

    try:
        # ── 2. Already initialized? ───────────────────────────────────────────
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="System already initialized. This endpoint is disabled.",
            )

        # ── 3. Roles — upsert pattern (safe even if partial data exists) ──────
        role_objs: dict[str, Role] = {}
        for role_name, desc in [
            ("ADMIN", "Full system access — manage users, override findings"),
            ("OFFICER", "Field inspection officer — create and submit inspections"),
        ]:
            res = await db.execute(select(Role).where(Role.role_name == role_name))
            role = res.scalar_one_or_none()
            if not role:
                role = Role(role_name=role_name, description=desc)
                db.add(role)
            role_objs[role_name] = role
        await db.commit()

        # ── 4. Admin user ─────────────────────────────────────────────────────
        admin = User(
            full_name=req.admin_full_name,
            email=req.admin_email,
            password_hash=get_password_hash(req.admin_password),
            roles=[role_objs["ADMIN"]],
        )
        db.add(admin)

        # ── 5. Default product category ───────────────────────────────────────
        res = await db.execute(
            select(ProductCategory).where(
                ProductCategory.category_name == "General Packaged Commodity"
            )
        )
        if not res.scalar_one_or_none():
            db.add(ProductCategory(
                category_name="General Packaged Commodity",
                description="Packaged goods under LMPC 2011 — net quantity, MRP, dates",
            ))

        await db.commit()

        # ── 6. Rule set + active version ──────────────────────────────────────
        res = await db.execute(
            select(RuleSet).where(RuleSet.name == "LMPC 2011 Standard")
        )
        ruleset = res.scalar_one_or_none()
        if not ruleset:
            ruleset = RuleSet(
                name="LMPC 2011 Standard",
                description="Legal Metrology (Packaged Commodities) Rules, 2011",
            )
            db.add(ruleset)
            await db.commit()
            await db.refresh(ruleset)

        res = await db.execute(
            select(RuleVersion).where(
                RuleVersion.rule_set_id == ruleset.id,
                RuleVersion.version_number == "1.0",
            )
        )
        if not res.scalar_one_or_none():
            db.add(RuleVersion(
                rule_set_id=ruleset.id,
                version_number="1.0",
                is_active=True,
            ))
            await db.commit()

    finally:
        # ── 7. Always release the lock — use a fresh connection ───────────────
        # We can't reuse `db` after a possible rollback, so open a new session.
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as unlock_db:
            await unlock_db.execute(
                text("SELECT pg_advisory_unlock(:key)"), {"key": _SETUP_LOCK_KEY}
            )
            await unlock_db.commit()

    return {
        "message": "System initialized successfully.",
        "admin_email": req.admin_email,
        "roles_created": list(role_objs.keys()),
        "hint": "POST /api/v1/auth/login to get your JWT token.",
    }
