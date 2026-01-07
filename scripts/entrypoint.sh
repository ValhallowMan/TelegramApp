#!/bin/bash
set -e

echo "🚀 Starting Auth Service initialization..."

# Ждём готовности PostgreSQL через Python + SQLAlchemy
echo "⏳ Waiting for PostgreSQL to accept connections..."
python - << 'PYTHON'
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def wait_for_postgres():
    attempts = 0
    max_attempts = 30
    while attempts < max_attempts:
        try:
            engine = create_async_engine(settings.DATABASE_URL, connect_args={"timeout": 5})
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            print("✅ PostgreSQL is ready and accepting connections")
            return True
        except Exception as e:
            attempts += 1
            print(f"   Attempt {attempts}/{max_attempts}: not ready yet ({str(e)[:100]})")
            await asyncio.sleep(2)
    print("❌ PostgreSQL failed to become ready after 30 attempts")
    sys.exit(1)

# Запускаем только одну asyncio.run
asyncio.run(wait_for_postgres())
PYTHON

# Если дошли сюда — БД готова
echo "🗄️ Applying database migrations..."
alembic upgrade head

echo "🌐 Starting Gunicorn server..."
exec gunicorn --config gunicorn.conf.py app.main:app