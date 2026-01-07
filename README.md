```markdown
# Auth Service API

Безопасный асинхронный сервис аутентификации на **FastAPI** с **PostgreSQL**, **Redis**, **JWT**-токенами, хэшированием паролей **Argon2** и полной поддержкой отзыва токенов.

## Возможности

- Регистрация и аутентификация пользователей
- Выдача пары JWT-токенов (access + refresh) с ротацией refresh-токена
- Полный отзыв токенов:
  - Выход с текущего устройства
  - Выход со всех устройств
  - Отзыв всех токенов аккаунта
- Админ-панель (управление пользователями, отзыв токенов)
- Защита от brute-force через rate limiting (FastAPI-Limiter + Redis)
- Миграции базы данных через Alembic
- Готов к запуску в Docker + Docker Compose
- Production-ready стартап (автоматические миграции, health checks)

## Технологии

- **FastAPI** — современный быстрый веб-фреймворк
- **SQLAlchemy 2.0** (async) + **asyncpg**
- **PostgreSQL** — основная база данных
- **Redis** — хранилище для rate limiting
- **Argon2** — безопасное хэширование паролей
- **PyJWT** (python-jose) — JWT-токены с уникальным JTI
- **Alembic** — миграции базы данных
- **Gunicorn + Uvicorn** — сервер для production
- **Docker Compose** — оркестрация контейнеров

## Быстрый запуск

### Требования

- Docker и Docker Compose
- Git

### 1. Клонируйте репозиторий

```bash
git clone https://github.com/yourusername/auth-service.git
cd auth-service
```

### 2. Создайте файл `.env`

Пример содержимого (обязательно смените пароли перед продакшеном!):

```env
# База данных
DB_HOST=postgres
DB_PORT=5432
DB_NAME=auth_db
DB_USER=auth_user
DB_PASSWORD=S3cr3tP@ssw0rd!2026

# Redis
REDIS_URL=redis://:verystrongredispassword2026@redis:6379/0

# Приложение
SECRET_KEY=очень_длинный_случайный_ключ_минимум_32_символа
ADMIN_PASSWORD=VeryStrongAdminPass!2026
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com

ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 3. Запустите сервисы

```bash
docker compose up --build -d
```

Сервис автоматически:

- Дождётся готовности PostgreSQL
- Применит миграции базы данных
- Создаст начального администратора
- Запустит API на порту 8000

### 4. Проверьте вход

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=VeryStrongAdminPass!2026"
```

Ожидаемый ответ:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### Документация API

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

### Основные эндпоинты

| Метод | Путь                                      | Описание                             | Требуется аутентификация |
|-------|-------------------------------------------|--------------------------------------|---------------------------|
| POST  | `/api/v1/auth/token`                      | Вход (получение access + refresh)    | Нет                       |
| POST  | `/api/v1/auth/refresh`                    | Обновление токенов                   | Refresh-токен             |
| POST  | `/api/v1/auth/logout`                     | Выход со всех устройств              | Access-токен              |
| POST  | `/api/v1/auth/logout-this-device`         | Выход только с текущего устройства   | Access-токен              |
| GET   | `/api/v1/admin/users`                     | Список пользователей                 | Админ                     |
| POST  | `/api/v1/admin/register`                  | Создание пользователя (админ)        | Админ                     |
| POST  | `/api/v1/admin/users/{id}/deactivate`     | Деактивация пользователя             | Админ                     |
| POST  | `/api/v1/admin/users/{id}/activate`       | Активация пользователя               | Админ                     |
| POST  | `/api/v1/admin/users/{id}/revoke-tokens`  | Отзыв всех токенов пользователя      | Админ                     |

## Разработка

### Создание новой миграции

```bash
docker compose exec app alembic revision --autogenerate -m "описание изменений"
```

### Применение миграций вручную

```bash
docker compose exec app alembic upgrade head
```

### Остановка сервисов

```bash
docker compose down
```

### Полная очистка (включая базу данных)

```bash
docker compose down --volumes
```

## Безопасность

- Все пароли хэшируются с помощью Argon2
- JWT-токены содержат уникальный JTI для возможности отзыва
- Refresh-токены хранятся в БД с ротацией
- Access-токены добавляются в blacklist при logout/refresh
- Rate limiting на эндпоинте входа
- Администратор не может деактивировать свой аккаунт