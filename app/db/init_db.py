from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import Base
from app.db.session import engine


async def create_tables_only(db: AsyncSession) -> None:
    """
    Только создаёт таблицы (идемпотентно).
    Используется только в dev/test, в продакшене — Alembic.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("🗄️ Database tables ensured (dev/test mode)")


# Если вдруг кто-то импортирует старую функцию — поднимем понятную ошибку
def init_db(*args, **kwargs):
    raise RuntimeError(
        "init_db() больше не используется в production. "
        "Используйте Alembic миграции: alembic upgrade head"
    )