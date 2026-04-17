"""HTTP routers — thin layer that parses requests and shapes responses."""

from app.routers import auth, setup

__all__ = ["auth", "setup"]
