from pydantic_settings import BaseSettings
from urllib.parse import quote_plus
from typing import Optional

class Settings(BaseSettings):
    DB_HOST: str = "postgres"
    DB_PORT: str = "5432"
    DB_NAME: str = "auth_db"
    DB_USER: str = "auth_user"
    DB_PASSWORD: str = "S3cr3tP@ssw0rd!2026"
   
    SECRET_KEY: str
    ADMIN_PASSWORD: str
    REDIS_URL: Optional[str] = "redis://redis:6379/0"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ADMIN_USERNAME: str = "admin"
    ADMIN_EMAIL: str = "admin@example.com"

    @property
    def DATABASE_URL(self):
        password = quote_plus(self.DB_PASSWORD)
        url = f"postgresql+asyncpg://{self.DB_USER}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        return url

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()