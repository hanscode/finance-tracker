"""
Finance Tracker — FastAPI Application Entry Point.

💡 CONCEPT: FastAPI vs Flask
   In Flask you wrote:
       app = Flask(__name__)
       @app.route('/pets', methods=['GET'])
       def get_pets():
           ...

   In FastAPI it's similar but more explicit:
       app = FastAPI()
       @app.get('/pets')
       def get_pets():
           ...

   Key differences:
   - HTTP methods are separate decorators (@app.get, @app.post, etc.)
   - Data types are validated automatically
   - Generates Swagger documentation at /docs automatically
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Code that runs on app startup and shutdown.

    💡 CONCEPT: Lifespan Events
       It's like Flask's @app.before_first_request but better.
       Code before `yield` runs on app STARTUP.
       Code after `yield` runs on app SHUTDOWN.
       Here we create the DB tables on startup.
    """
    # Startup: create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    print(f"✓ {settings.APP_NAME} started")
    print(f"✓ Database: {settings.DATABASE_URL}")
    yield
    # Shutdown: cleanup if needed
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


@app.get("/api/health")
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
