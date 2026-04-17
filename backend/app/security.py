"""
Security primitives — password hashing, JWT, token generation/hashing.

This module is the ONLY place that deals with crypto. Every other module
(routers, services) imports from here. That way if we need to swap bcrypt
for argon2, or JWT for opaque tokens, we change one file.

💡 CONCEPT: Separation of concerns
   Instead of scattering `bcrypt.hash()` calls across the codebase, we
   centralize them. This is the same principle as `database.py` being the
   only place that creates SQLAlchemy engines.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from pwdlib import PasswordHash

from app.config import settings

# ============================================================
# Password hashing (bcrypt via pwdlib)
# ============================================================
#
# 💡 CONCEPT: pwdlib vs raw bcrypt
#    `pwdlib` is a modern wrapper around bcrypt/argon2. It replaces the
#    abandoned `passlib` package. Benefits:
#    - Active maintenance, supports latest bcrypt (5.x)
#    - `.recommended()` uses bcrypt with sensible defaults
#    - Easy to migrate to argon2 later without changing call sites
#
# 💡 CONCEPT: .recommended() vs manual config
#    PasswordHash.recommended() picks today's best defaults. If in 2 years
#    argon2 becomes the preferred choice, just updating pwdlib gives us
#    the improvement automatically.

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt.

    The result is a self-contained string (~60 chars) that includes:
    - The algorithm version: "$2b$"
    - The cost factor: "$12$" (2^12 = 4096 rounds; higher = slower = safer)
    - The salt: 22 chars (random, different per password)
    - The hash: 31 chars

    Example output:
        $2b$12$KlhRj8NXyZ.randomsalt.randomhash...

    No need to store the salt separately — it's part of the hash string.
    """
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check if a plaintext password matches a stored hash.

    bcrypt automatically extracts the salt from `hashed_password`, hashes
    the plaintext with it, and compares. We never touch salts manually.

    Returns True if the password is correct, False otherwise.
    """
    return password_hash.verify(plain_password, hashed_password)


# ============================================================
# JWT (JSON Web Tokens)
# ============================================================
#
# 💡 CONCEPT: JWT vs session cookies
#    A JWT is a signed JSON payload. The server issues it on login and
#    the client sends it back on every request. The server verifies the
#    signature (using SECRET_KEY) to know the payload wasn't tampered with.
#
#    Key insight: JWTs are STATELESS. The server doesn't need to look up
#    a session in a database — the user's identity is IN the token.
#
#    Trade-off: revoking a JWT before it expires requires extra work
#    (we'll use the `sessions` table for that).


def create_access_token(
    user_id: int,
    session_token: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT containing the user ID and a session reference.

    💡 CONCEPT: Why include `session_token`?
       We could put just `user_id` in the JWT and call it a day. But then
       logging out would be impossible — the JWT stays valid until expiry.

       Instead, we also include a session identifier. On every authenticated
       request, we look up the session in the DB. If the user logs out, we
       delete the session row, making the JWT effectively invalid.

       This gives us: JWT's speed (most requests skip DB lookups for auth)
       PLUS the ability to revoke.

    Args:
        user_id: The authenticated user's ID
        session_token: The raw session token (we hash it separately for DB lookup)
        expires_delta: How long the token is valid. Defaults to config value.

    Returns:
        A signed JWT string: "eyJhbGc...xyz.abc"
    """
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload: dict[str, Any] = {
        "sub": str(user_id),          # "sub" (subject) is the JWT standard for user ID
        "sid": session_token,          # custom claim: session identifier
        "exp": expire,                 # "exp" (expiry) — jose auto-converts to int timestamp
        "iat": datetime.now(UTC),  # "iat" (issued at)
    }

    # jose signs the payload with the secret using the configured algorithm (HS256)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Verify a JWT's signature and return its payload.

    Returns the decoded payload if valid, None if:
    - Signature doesn't match (tampered or wrong secret)
    - Expired
    - Malformed

    We return None instead of raising so callers can choose how to respond
    (typically with a 401 Unauthorized).
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError:
        # Catches all jose errors: expired, invalid signature, malformed, etc.
        return None


# ============================================================
# Random tokens (for sessions and magic links)
# ============================================================
#
# 💡 CONCEPT: secrets module vs random
#    Python has `random` (predictable, for games/simulations) and `secrets`
#    (cryptographically secure, for tokens/passwords).
#
#    ALWAYS use `secrets` for anything security-related. `random` is
#    seedable and predictable — an attacker who knows the seed could
#    guess "random" tokens.


def generate_session_token() -> str:
    """Generate a cryptographically-secure random token.

    Uses `secrets.token_urlsafe` which returns URL-safe base64 without
    padding. 32 bytes = 256 bits of entropy, encoded as ~43 characters.

    That's far more than enough to prevent guessing.
    """
    return secrets.token_urlsafe(32)


def generate_magic_link_token() -> str:
    """Generate a token for magic link emails.

    Same as session tokens but named separately because they may diverge
    later (e.g., different length or encoding).
    """
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 hash a token for safe DB storage.

    💡 CONCEPT: Why hash tokens in the DB?
       If an attacker dumps our database, they should NOT be able to
       impersonate active sessions. Storing only the hash makes the
       stolen data useless for impersonation.

       Flow:
       1. Server generates raw token: "abc123..."
       2. Server stores sha256("abc123...") in DB
       3. Server sends raw "abc123..." to client (in JWT or email)
       4. Client includes token in requests
       5. Server hashes incoming token, looks up DB by hash

       SHA-256 is fine here (unlike passwords) because:
       - Tokens have high entropy (32 bytes of randomness)
       - They expire quickly
       - Rainbow table attacks don't apply

       For passwords we need bcrypt because humans pick low-entropy ones.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
