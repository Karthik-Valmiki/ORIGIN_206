from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

import os
from app.api.v1 import auth, inspections, setup, admin
from app.config import settings
from app.database import engine, AsyncSessionLocal
from app.core.security import get_password_hash, verify_password

from fastapi.responses import RedirectResponse


async def _seed_database():
    """
    Idempotent startup seed:
    - Ensure ADMIN and OFFICER roles exist.
    - Ensure the hardcoded admin account exists (and password stays in sync).
    - Ensure default ProductCategory, RuleSet & RuleVersion exist.
    """
    from app.models.user import User, Role
    from app.models.inspection import ProductCategory, RuleSet, RuleVersion, Rule

    async with AsyncSessionLocal() as db:
        # ── 1. Roles ──────────────────────────────────────────────────────────
        for role_name, desc in [
            ("ADMIN",   "Full system access — manage users, override findings"),
            ("OFFICER", "Field inspection officer — create and submit inspections"),
        ]:
            res = await db.execute(select(Role).where(Role.role_name == role_name))
            if not res.scalar_one_or_none():
                db.add(Role(role_name=role_name, description=desc))
        await db.commit()

        # ── 2. Hardcoded Admin user ───────────────────────────────────────────
        admin_email = settings.ADMIN_EMAIL.lower().strip()
        res = await db.execute(
            select(User)
            .where(func.lower(User.email) == admin_email)
            .options(selectinload(User.roles))
        )
        existing_admin = res.scalar_one_or_none()

        admin_role = (
            await db.execute(select(Role).where(Role.role_name == "ADMIN"))
        ).scalar_one()

        if existing_admin is None:
            new_admin = User(
                full_name=settings.ADMIN_FULL_NAME,
                email=admin_email,
                password_hash=get_password_hash(settings.ADMIN_PASSWORD),
                is_active=True,
                roles=[admin_role],
            )
            db.add(new_admin)
            await db.commit()
            print(f"  ✅ Admin account seeded: {admin_email}")
        else:
            # Keep password hash in sync with config (in case it changes)
            if not verify_password(settings.ADMIN_PASSWORD, existing_admin.password_hash):
                existing_admin.password_hash = get_password_hash(settings.ADMIN_PASSWORD)
                await db.commit()
                print(f"  🔄 Admin password re-synced for: {admin_email}")
            else:
                print(f"  ✅ Admin account already present: {admin_email}")

        # ── 3. Default product category ───────────────────────────────────────
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

        # ── 4. Rule set + active version ──────────────────────────────────────
        res = await db.execute(select(RuleSet).where(RuleSet.name == "LMPC 2011 Standard"))
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
        active_ver = res.scalar_one_or_none()
        if not active_ver:
            active_ver = RuleVersion(rule_set_id=ruleset.id, version_number="1.0", is_active=True)
            db.add(active_ver)
            await db.commit()
            await db.refresh(active_ver)

        # ── 5. Standard LMPC Rules ────────────────────────────────────────────
        standard_rules = [
            {
                "rule_code": "LMPC_RULE_6_1_E",
                "check_type": "DECLARATION",
                "description": "Maximum Retail Price (MRP) inclusive of all taxes must be declared.",
                "parameters": {"rule_ref": "Rule 6(1)(e)", "field": "MRP", "is_mandatory": True},
            },
            {
                "rule_code": "LMPC_RULE_6_1_B",
                "check_type": "PRESENCE",
                "description": "Net quantity in standard units of weight or measure must be declared.",
                "parameters": {"rule_ref": "Rule 6(1)(b)", "field": "QUANTITY", "is_mandatory": True},
            },
            {
                "rule_code": "LMPC_RULE_6_1_C",
                "check_type": "DECLARATION",
                "description": "Name and complete address of the manufacturer or packer must be declared.",
                "parameters": {"rule_ref": "Rule 6(1)(c)", "field": "MANUFACTURER", "is_mandatory": True},
            },
            {
                "rule_code": "LMPC_RULE_6_1_D",
                "check_type": "FORMAT",
                "description": "Month and year of manufacture or packing must be declared.",
                "parameters": {"rule_ref": "Rule 6(1)(d)", "field": "DATES", "is_mandatory": False},
            },
            {
                "rule_code": "LMPC_RULE_6_1_G",
                "check_type": "DECLARATION",
                "description": "Name, address, telephone number, and email of consumer care cell.",
                "parameters": {"rule_ref": "Rule 6(1)(g)", "field": "CONSUMER_CARE", "is_mandatory": False},
            },
            {
                "rule_code": "LMPC_RULE_6_1_A",
                "check_type": "DECLARATION",
                "description": "Common or generic name of the commodity contained in the package.",
                "parameters": {"rule_ref": "Rule 6(1)(a)", "field": "PRODUCT_NAME", "is_mandatory": False},
            },
            {
                "rule_code": "LMPC_RULE_6_1_F",
                "check_type": "DECLARATION",
                "description": "Name of the country of origin or manufacture (for imported packages).",
                "parameters": {"rule_ref": "Rule 6(1)(f)", "field": "COUNTRY_OF_ORIGIN", "is_mandatory": False},
            },
        ]

        for r_data in standard_rules:
            existing_r = await db.execute(
                select(Rule).where(
                    Rule.rule_version_id == active_ver.id,
                    Rule.rule_code == r_data["rule_code"],
                )
            )
            if not existing_r.scalar_one_or_none():
                db.add(Rule(
                    rule_version_id=active_ver.id,
                    rule_code=r_data["rule_code"],
                    check_type=r_data["check_type"],
                    description=r_data["description"],
                    parameters=r_data["parameters"],
                ))
        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    print("\n" + "=" * 50)
    print(" LMPC Backend is running!")
    print(" Interactive Swagger UI: http://localhost:8000/docs")
    print("  Health Check:           http://localhost:8000/health")
    print("=" * 50)
    print("\n  Seeding database…")
    try:
        await _seed_database()
    except Exception as exc:
        print(f"  ⚠️  Seed error (non-fatal): {exc}")
    print("=" * 50 + "\n")
    yield
    await engine.dispose()


app = FastAPI(
    title="LMPC Verification System Prototype",
    description="Backend API for OCR and CV processing (SIH 2026)",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(setup.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(inspections.router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root():
    """Automatically redirect root requests to Swagger UI documentation."""
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
