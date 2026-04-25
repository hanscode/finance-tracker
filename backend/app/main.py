"""Finance Tracker — FastAPI application entry point.

Key things to know about FastAPI used here:
- HTTP methods are separate decorators (@app.get, @app.post, etc.)
- Request/response bodies are validated automatically via Pydantic
- Swagger UI is auto-generated at /docs
- Lifespan context manager (below) replaces the older @app.on_event hooks
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, category, setup, transaction


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Code that runs on app startup and shutdown.

    💡 CONCEPT: Lifespan Events
       Code before `yield` runs on app STARTUP.
       Code after `yield` runs on app SHUTDOWN.

    💡 CONCEPT: Why we don't call create_all() anymore
       In the initial setup we used `Base.metadata.create_all(engine)` to
       auto-create tables. That's fine to bootstrap, but it doesn't track
       schema changes over time.

       Now that we have Alembic, the workflow is:
           docker compose exec backend alembic upgrade head

       This applies any pending migrations. Much better for real projects
       because you get proper versioning and rollback support.
    """
    print(f"✓ {settings.APP_NAME} started")
    print(f"✓ Database: {settings.DATABASE_URL}")
    yield
    print(f"✗ {settings.APP_NAME} shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    description="Personal finance tracking API — self-hosted, private, yours.",
    version="0.1.0",
    lifespan=lifespan,
)


# CORS Middleware — allows the frontend (localhost:5173) to make requests to the backend
# Without this, the browser blocks requests for security (Same-Origin Policy)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],
)


# ============================================================
# Routers — each feature lives in its own module under app/routers/
# ============================================================
#
# 💡 CONCEPT: include_router
#    Each router is a self-contained group of endpoints (prefix + tags).
#    We register them on the main app here. As we add features
#    (transactions, categories, etc.), we'll include more routers.
app.include_router(setup.router)
app.include_router(auth.router)
app.include_router(category.router)
app.include_router(transaction.router)


@app.get("/api/health", tags=["health"])
def health_check():
    """
    Health check endpoint — verifies the API is running.

    Visit http://localhost:8000/api/health to see it in action.
    Visit http://localhost:8000/docs to see the Swagger documentation.
    """
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "0.1.0",
    }
