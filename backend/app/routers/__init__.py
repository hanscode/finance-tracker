"""HTTP routers — thin layer that parses requests and shapes responses."""

from app.routers import auth, category, setup

__all__ = ["auth", "category", "setup"]
