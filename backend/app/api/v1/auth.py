from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.deps import get_db, require_role
from app.models.user import User, Role
from app.schemas.auth import TokenResponse, UserCreate, UserOut, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Find the role
    role_result = await db.execute(select(Role).where(Role.role_name == user_data.role_name))
    role = role_result.scalar_one_or_none()
    if not role:
        # Create it if it doesn't exist just for the prototype's ease
        role = Role(role_name=user_data.role_name)
        db.add(role)
        await db.commit()
        await db.refresh(role)

    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        password_hash=hashed_password,
        roles=[role]
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # get roles for token
    await db.refresh(user, ['roles'])
    roles = [r.role_name for r in user.roles]
    
    access_token = create_access_token(
        subject=str(user.id),
        roles=roles
    )
    return LoginResponse(
        access_token=access_token, 
        user=user
    )
