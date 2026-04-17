# ============================================
# Finance Tracker — Backend Dockerfile
# ============================================
#
# 💡 CONCEPT: Multi-stage Builds
#    We use "stages" to separate the development image
#    from the production one. This is what Campfire and
#    Writebook from 37signals do.
#
#    - Stage "base": system dependencies + pip install
#    - Stage "dev": runs uvicorn with --reload (hot reload)
#    - Stage "prod": minimal image for production

# ---- Base stage: install dependencies ----
FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies for SQLite
RUN apt-get update && \
    apt-get install -y --no-install-recommends libsqlite3-0 && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Development stage ----
FROM base AS dev

# Install dev-only tools (ruff, mypy, rich) for linting/formatting inside
# VSCode Dev Containers. These are NOT included in the prod stage.
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy source code (in dev, overridden by volume mount)
COPY . .

# Uvicorn port
EXPOSE 8000

# --reload: restarts the server when you change code
# --host 0.0.0.0: accepts connections from outside the container
CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]

# ---- Production stage ----
FROM base AS prod

COPY . .

EXPOSE 8000

# No --reload in production (faster and more stable)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
