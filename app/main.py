# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from redis.asyncio import from_url as redis_from_url
from fastapi_limiter import FastAPILimiter  # ← добавьте импорт
from app.core.config import settings
from app.api.v1 import router as api_v1_router
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = redis_from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis)
    yield 
    await FastAPILimiter.close()
    await engine.dispose()


app = FastAPI(
    title="Auth Service API",
    description="Secure asynchronous authentication service with Argon2 and JWT",
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Auth Service API", "version": "1.1.0", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "auth"}