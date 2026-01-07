# app/crud/token.py
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.token import RefreshToken, BlacklistedToken


# === Refresh Tokens ===

async def create_refresh_token_record(
    db: AsyncSession,
    user_id: int,
    jti: str,
    expires_at: datetime,
    current_access_jti: str  # ← новый параметр
) -> RefreshToken:
    db_token = RefreshToken(
        user_id=user_id,
        jti=jti,
        expires_at=expires_at,
        created_at=datetime.now(timezone.utc),
        current_access_jti=current_access_jti
    )
    db.add(db_token)
    await db.commit()
    await db.refresh(db_token)
    return db_token


async def get_valid_refresh_token(
    db: AsyncSession,
    user_id: int,
    jti: str
) -> Optional[RefreshToken]:
    """Получить активный refresh-токен по jti"""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.jti == jti,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > now
        )
    )
    token = result.scalar_one_or_none()
    if token:
        token.last_used_at = now
        await db.commit()
    return token


async def revoke_refresh_token_by_jti(db: AsyncSession, jti: str) -> bool:
    """Отозвать refresh-токен по jti"""
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.jti == jti)
    )
    token = result.scalar_one_or_none()
    if token and not token.is_revoked:
        token.is_revoked = True
        await db.commit()
        return True
    return False


async def revoke_all_user_refresh_tokens(db: AsyncSession, user_id: int) -> int:
    """Отозвать все активные refresh-токены пользователя"""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > now
        )
    )
    tokens = result.scalars().all()
    for token in tokens:
        token.is_revoked = True
    if tokens:
        await db.commit()
    return len(tokens)


# === Blacklisted Tokens (для access-токенов) ===

async def blacklist_access_token(
    db: AsyncSession,
    jti: str,
    user_id: int,
    expires_at: datetime,
    reason: Optional[str] = None
) -> Optional[BlacklistedToken]:
    """Добавить access-токен в blacklist по jti"""
    # Проверка дубликата
    existing = await db.execute(
        select(BlacklistedToken).where(BlacklistedToken.jti == jti)
    )
    if existing.scalar_one_or_none():
        return None

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    db_token = BlacklistedToken(
        jti=jti,
        user_id=user_id,
        expires_at=expires_at,
        reason=reason,
        blacklisted_at=datetime.now(timezone.utc)
    )
    db.add(db_token)
    await db.commit()
    await db.refresh(db_token)
    return db_token


async def is_token_blacklisted(db: AsyncSession, jti: str) -> bool:
    """Проверить, в чёрном ли списке access-токен по jti"""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(BlacklistedToken).where(
            BlacklistedToken.jti == jti,
            BlacklistedToken.expires_at > now
        )
    )
    return result.scalar_one_or_none() is not None


# === Общие утилиты ===

async def revoke_all_user_tokens(db: AsyncSession, user_id: int) -> dict:
    """
    Полный отзыв токенов пользователя:
    - Отзыв всех refresh-токенов
    - Установка tokens_revoked_at у пользователя
    Возвращает статистику.
    """
    from app.models.user import User
    from app.crud.user import deactivate_user  # Только если нужно деактивировать

    # Отзыв refresh-токенов
    refresh_revoked = await revoke_all_user_refresh_tokens(db, user_id)

    # Обновление пользователя
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user.tokens_revoked_at = datetime.now(timezone.utc)
        await db.commit()

    return {
        "refresh_tokens_revoked": refresh_revoked,
        "account_tokens_revoked_at": user.tokens_revoked_at if user else None
    }


async def cleanup_expired_refresh_tokens(db: AsyncSession) -> int:
    """Пометить просроченные refresh-токены как отозванные"""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.expires_at <= now,
            RefreshToken.is_revoked == False
        )
    )
    tokens = result.scalars().all()
    for token in tokens:
        token.is_revoked = True
    if tokens:
        await db.commit()
    return len(tokens)


async def cleanup_expired_blacklisted_tokens(db: AsyncSession) -> int:
    """Удалить просроченные записи из blacklist"""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(BlacklistedToken).where(BlacklistedToken.expires_at <= now)
    )
    tokens = result.scalars().all()
    for token in tokens:
        await db.delete(token)
    if tokens:
        await db.commit()
    return len(tokens)