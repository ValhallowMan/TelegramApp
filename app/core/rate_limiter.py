# app/core/rate_limiter.py
from fastapi import Request, HTTPException, status
from fastapi_limiter.depends import RateLimiter
from typing import Callable

def login_rate_limiter() -> Callable:
    """
    Rate limit для логина:
    - 10 попыток в минуту по IP
    - 5 попыток в минуту по username (защита конкретного аккаунта)
    - Комбинированный ключ IP + username
    """
    async def identifier(request: Request):
        # Получаем username из формы (OAuth2PasswordRequestForm)
        form = await request.form()
        username = form.get("username", "unknown")
        forwarded = request.headers.get("X-Forwarded-For")
        ip = forwarded.split(",")[0] if forwarded else request.client.host
        return f"login:{ip}:{username}"

    return RateLimiter(
        times=8,          # максимум 8 попыток
        minutes=1,        # за 1 минуту
        identifier=identifier,  # кастомный ключ: IP + username
        # optional: error_message="Слишком много попыток входа. Попробуйте позже."
    )