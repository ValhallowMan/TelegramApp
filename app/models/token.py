# app/models/token.py
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Boolean,
    Index, UniqueConstraint
)
from sqlalchemy.sql import func
from app.db.base import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    jti = Column(String, nullable=False, index=True)  # ← заменяет token_hash
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    is_revoked = Column(Boolean, default=False)

    # Составной индекс для быстрого поиска активных токенов пользователя
    __table_args__ = (
        Index("ix_refresh_active_user", "user_id", "is_revoked", "expires_at"),
        UniqueConstraint("jti", name="uq_refresh_jti"),
    )
    current_access_jti = Column(String, nullable=True, index=True)


class BlacklistedToken(Base):
    __tablename__ = "blacklisted_tokens"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String, nullable=False, unique=True, index=True)  # ← вместо token_hash
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    blacklisted_at = Column(DateTime(timezone=True), server_default=func.now())
    reason = Column(String, nullable=True)

    # Индекс для очистки по сроку
    __table_args__ = (
        Index("ix_blacklist_expires", "expires_at"),
    )