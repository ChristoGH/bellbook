from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from app.api import announcements as announcements_router
from app.api import auth as auth_router
from app.api import events as events_router
from app.config import settings
from app.middleware.school_context import SchoolContextMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create Redis connection pool
    app.state.redis = Redis.from_url(settings.REDIS_URL, decode_responses=False)
    yield
    # Shutdown: close Redis pool
    await app.state.redis.aclose()


app = FastAPI(title="BellBook API", version="0.1.0", lifespan=lifespan)

# Middleware (outermost first — school context must run before route handlers)
app.add_middleware(SchoolContextMiddleware)

# Routers
app.include_router(auth_router.router)
app.include_router(announcements_router.router)
app.include_router(events_router.router)


@app.get("/api/health")
async def health() -> dict:
    redis: Redis = app.state.redis
    try:
        await redis.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    return {"status": "ok", "redis": redis_ok}
