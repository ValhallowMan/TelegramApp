# app/api/v1/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.deps import get_db, get_current_admin
from app.schemas.user import UserCreate, UserResponse
from app.crud.user import get_user_by_username, get_user_by_email, create_user, get_user_by_id
from app.crud.token import revoke_all_user_tokens
from app.models.user import User
from app.crud.user import deactivate_user, activate_user


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    from app.crud.user import get_users
    users = await get_users(db, skip=skip, limit=limit)
    return users


@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    if await get_user_by_username(db, user_data.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    if await get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = await create_user(db, user_data)
    return user


@router.post("/users/{user_id}/deactivate")
async def deactivate_user_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await deactivate_user(db, user_id)  # ← использует обновлённый CRUD
    return {"message": f"User {user.username} deactivated"}


@router.post("/users/{user_id}/activate")
async def activate_user_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await activate_user(db, user_id)
    return {"message": f"User {user.username} activated"}


@router.post("/users/{user_id}/revoke-tokens")
async def revoke_user_tokens(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = await revoke_all_user_tokens(db, user_id)
    return {
        "message": f"Revoked tokens for user {user.username}",
        "refresh_tokens_revoked": result["refresh_tokens_revoked"]
    }