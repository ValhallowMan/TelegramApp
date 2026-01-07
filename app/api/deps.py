# API-level зависимости
from fastapi import Header, HTTPException


async def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != "your-api-key":  # В реальном проекте из конфига
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key