# Auth Service

## Setup
1. cp .env.example .env
2. docker-compose up -d
3. alembic upgrade head

## Endpoints
- POST /api/v1/auth/token: Login
- POST /api/v1/auth/refresh: Refresh
- GET /api/v1/admin/users: Admin users (protected)