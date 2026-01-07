from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select  # для ORM-запросов
from app.core import security
from app.core.config import settings
from app.core.deps import get_db, get_current_user
from app.schemas.token import Token, RefreshTokenRequest
from app.crud.user import authenticate_user
from app.crud.token import (
    create_refresh_token_record,
    get_valid_refresh_token,
    revoke_refresh_token_by_jti,
    blacklist_access_token,
    revoke_all_user_tokens,
)
from app.models.user import User
from app.models.token import RefreshToken
from app.core.rate_limiter import login_rate_limiter

router = APIRouter()


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    limiter: None = Depends(login_rate_limiter()),
    db: AsyncSession = Depends(get_db),
):
    """Логин: выдача пары access + refresh токенов"""
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # При успешном входе сбрасываем глобальный отзыв токенов (если был)
    if user.tokens_revoked_at is not None:
        user.tokens_revoked_at = None
        await db.commit()

    # Создаём токены
    access_token = security.create_access_token(data={"sub": str(user.id)})
    refresh_token = security.create_refresh_token(data={"sub": str(user.id)})

    # Получаем payload'ы (без проверки exp)
    access_payload = security.get_token_payload(access_token)
    refresh_payload = security.get_token_payload(refresh_token)

    access_jti = access_payload["jti"]
    refresh_jti = refresh_payload["jti"]
    refresh_expires_at = datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc)

    # Сохраняем refresh-токен в БД вместе с текущим access_jti
    await create_refresh_token_record(
        db=db,
        user_id=user.id,
        jti=refresh_jti,
        expires_at=refresh_expires_at,
        current_access_jti=access_jti,  # ← ключевой момент
    )

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Обновление токенов: ротация refresh + отзыв старого access"""
    payload = security.verify_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = int(payload["sub"])
    refresh_jti = payload.get("jti")
    if not refresh_jti:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Corrupted token")

    # Проверяем валидность refresh-токена в БД
    db_token = await get_valid_refresh_token(db, user_id, refresh_jti)
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked, expired or not found",
        )

    # === КРИТИЧЕСКИ ВАЖНО: отзываем СТАРЫЙ access-токен ===
    if db_token.current_access_jti:
        # exp берём из текущего (старого) refresh-токена — access живёт меньше, так что безопасно
        old_access_expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        await blacklist_access_token(
            db=db,
            jti=db_token.current_access_jti,
            user_id=user_id,
            expires_at=old_access_expires_at,
            reason="token_refresh_rotation",
        )

    # Отзываем использованный refresh-токен
    await revoke_refresh_token_by_jti(db, refresh_jti)

    # Генерируем новые токены
    new_access_token = security.create_access_token(data={"sub": str(user_id)})
    new_refresh_token = security.create_refresh_token(data={"sub": str(user_id)})

    new_access_payload = security.get_token_payload(new_access_token)
    new_refresh_payload = security.get_token_payload(new_refresh_token)

    new_access_jti = new_access_payload["jti"]
    new_refresh_jti = new_refresh_payload["jti"]
    new_refresh_expires_at = datetime.fromtimestamp(new_refresh_payload["exp"], tz=timezone.utc)

    # Сохраняем новый refresh с привязкой к новому access_jti
    await create_refresh_token_record(
        db=db,
        user_id=user_id,
        jti=new_refresh_jti,
        expires_at=new_refresh_expires_at,
        current_access_jti=new_access_jti,
    )

    return Token(access_token=new_access_token, refresh_token=new_refresh_token)


@router.post("/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Выход из всех устройств: отзыв всех токенов пользователя"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing access token")

    access_token = auth_header[len("Bearer "):].strip()
    payload = security.get_token_payload(access_token)

    if not payload or "jti" not in payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid access token")

    access_jti = payload["jti"]
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

    # 1. Blacklist текущего access-токена
    await blacklist_access_token(
        db=db,
        jti=access_jti,
        user_id=current_user.id,
        expires_at=expires_at,
        reason="explicit_logout",
    )

    # 2. Полный отзыв всех токенов пользователя (все устройства)
    result = await revoke_all_user_tokens(db, current_user.id)

    return {
        "message": "Successfully logged out from all devices",
        "current_access_token_revoked": True,
        "refresh_tokens_revoked_count": result["refresh_tokens_revoked"],
        "all_future_tokens_blocked": True,
    }


@router.post("/logout-this-device")
async def logout_this_device(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Выход только с текущего устройства:
    - Отзывает текущий access-токен
    - Отзывает связанный с ним refresh-токен (по current_access_jti)
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing access token")

    access_token = auth_header[len("Bearer "):].strip()
    access_payload = security.get_token_payload(access_token)

    if not access_payload or "jti" not in access_payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid access token")

    access_jti = access_payload["jti"]
    access_expires_at = datetime.fromtimestamp(access_payload["exp"], tz=timezone.utc)

    # 1. Добавляем текущий access-токен в blacklist
    await blacklist_access_token(
        db=db,
        jti=access_jti,
        user_id=current_user.id,
        expires_at=access_expires_at,
        reason="logout_this_device",
    )

    # 2. Ищем активный refresh-токен по current_access_jti (ORM-стиль)
    now = datetime.now(timezone.utc)
    stmt = (
        select(RefreshToken.jti)
        .where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.current_access_jti == access_jti,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > now,
        )
    )
    result = await db.execute(stmt)
    row = result.fetchone()

    refresh_revoked = False
    if row:
        refresh_jti = row[0]
        await revoke_refresh_token_by_jti(db, refresh_jti)
        refresh_revoked = True

    return {
        "message": "Successfully logged out from this device",
        "access_token_revoked": True,
        "refresh_token_revoked": refresh_revoked,
        "note": "Associated refresh token not found or already revoked" if not refresh_revoked else None,
    }