from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import Role, User
from app.schemas.auth import LoginRequest, LoginResponse, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


async def _authenticate_and_create_token(
    email: str, password: str, db: AsyncSession
) -> LoginResponse:
    normalized_email = email.lower().strip()
    result = await db.execute(
        select(User)
        .where(func.lower(User.email) == normalized_email)
        .options(selectinload(User.roles))
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Contact an administrator.",
        )

    roles = [r.role_name.upper() for r in user.roles]
    access_token = create_access_token(
        subject=str(user.id),
        roles=roles,
    )
    return LoginResponse(access_token=access_token, user=user)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    normalized_email = user_data.email.lower().strip()

    # Prevent privilege escalation: self-registration is strictly for OFFICER role
    requested_role = user_data.role_name.upper().strip()
    if requested_role != "OFFICER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration is only permitted for the OFFICER role. ADMIN accounts must be provisioned by an administrator.",
        )

    # Check for duplicate email
    existing = await db.execute(
        select(User).where(func.lower(User.email) == normalized_email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Find the role
    role_result = await db.execute(
        select(Role).where(Role.role_name == requested_role)
    )
    role = role_result.scalar_one_or_none()
    if not role:
        # Create default OFFICER role if not yet seeded
        role = Role(
            role_name="OFFICER",
            description="Field inspection officer — create and submit inspections",
        )
        db.add(role)
        await db.commit()
        await db.refresh(role)

    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        full_name=user_data.full_name.strip(),
        email=normalized_email,
        password_hash=hashed_password,
        roles=[role],
    )
    db.add(new_user)
    await db.commit()

    # Re-fetch with selectinload to prevent MissingGreenlet error on response serialization
    res = await db.execute(
        select(User).where(User.id == new_user.id).options(selectinload(User.roles))
    )
    return res.scalar_one()


@router.post("/login", response_model=LoginResponse)
async def login_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """OAuth2 form-data login endpoint (used by Swagger UI and standard OAuth2 clients)."""
    return await _authenticate_and_create_token(
        email=form_data.username,
        password=form_data.password,
        db=db,
    )


@router.post("/login/json", response_model=LoginResponse)
async def login_json(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """JSON login endpoint for single-page apps and mobile clients."""
    return await _authenticate_and_create_token(
        email=body.email,
        password=body.password,
        db=db,
    )


@router.get("/me", response_model=UserOut)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Returns profile and roles of the currently authenticated user."""
    return current_user

