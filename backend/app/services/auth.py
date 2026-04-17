"""
Authentication service — login, session management, user lookup.

💡 CONCEPT: Why split auth logic from the router
   The router (HTTP layer) should be thin: parse the request, call the
   service, shape the response. All the "how do I verify credentials",
   "how do I create a session row" logic lives here.

   Benefit: we can call `authenticate_user()` from a test, a CLI script,
   or a future gRPC server — without touching HTTP.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session as DbSession

from app import security
from app.config import settings
from app.models import Session as UserSession
from app.models import User


def authenticate_user(
    db: DbSession,
    *,
    email: str,
    password: str,
) -> User | None:
    """Check credentials. Returns the User if valid, None otherwise.

    Why None instead of raising? Because "wrong password" isn't an
    exceptional case — it's a normal outcome. The router layer decides
    how to turn None into an HTTP 401 response.

    💡 CONCEPT: Constant-time comparison
       We always call `verify_password` even if the user doesn't exist,
       using a dummy hash. This prevents "timing attacks" where an
       attacker could tell whether an email exists by measuring response
       times (real user → 100ms of bcrypt work, missing user → 1ms).
    """
    # Normalize the email the same way we stored it
    user = (
        db.query(User)
        .filter(User.email == email.lower())
        .first()
    )

    if user is None:
        # Burn some CPU hashing against a fake password so the response
        # time is similar to a real (but failed) login. Defense vs timing attacks.
        security.verify_password(password, _DUMMY_HASH)
        return None

    if not user.is_active:
        return None

    if user.password_hash is None:
        # Magic-link-only user tried to log in with password
        return None

    if not security.verify_password(password, user.password_hash):
        return None

    return user


def create_session(
    db: DbSession,
    *,
    user: User,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[str, UserSession]:
    """Create a new session row + issue a session token.

    Returns:
        (raw_token, session_row)
        - raw_token: to be put inside a JWT and sent to the client
        - session_row: the DB record, mainly for testing/debugging

    Workflow:
        1. Generate a random token (high entropy, unguessable)
        2. Hash it (SHA-256) and store the HASH in the DB
        3. Return the raw token — the caller embeds it in a JWT

    💡 CONCEPT: Rotating sessions on each login
       We could reuse an existing active session, but creating a fresh
       one on every login is safer. If someone stole the old token, it
       won't let them back in after a legitimate re-login.
    """
    raw_token = security.generate_session_token()
    token_hash = security.hash_token(raw_token)

    now = datetime.now(UTC)
    session_row = UserSession(
        user_id=user.id,
        token_hash=token_hash,
        user_agent=user_agent,
        ip_address=ip_address,
        expires_at=now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        last_activity_at=now,
    )
    db.add(session_row)

    # Update last_login_at on the user
    user.last_login_at = now

    db.commit()
    db.refresh(session_row)

    return raw_token, session_row


def get_user_from_jwt(db: DbSession, *, jwt_token: str) -> User | None:
    """Given a JWT, return the authenticated User (or None if invalid).

    Steps:
    1. Verify the JWT signature and extract the payload
    2. Look up the session by its hash — must exist and not be expired
    3. Look up the user

    Any step failing returns None; the router turns that into 401.
    """
    # 1. Verify JWT signature
    payload = security.decode_access_token(jwt_token)
    if payload is None:
        return None

    user_id_str = payload.get("sub")
    session_token = payload.get("sid")
    if not user_id_str or not session_token:
        return None

    try:
        user_id = int(user_id_str)
    except (TypeError, ValueError):
        return None

    # 2. Validate the session exists and isn't expired
    token_hash = security.hash_token(session_token)
    now = datetime.now(UTC)

    session_row = (
        db.query(UserSession)
        .filter(
            UserSession.token_hash == token_hash,
            UserSession.user_id == user_id,
            UserSession.expires_at > now,
        )
        .first()
    )

    if session_row is None:
        return None

    # 3. Load the user and confirm they're still active
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        return None

    # Update session activity (useful for "active sessions" UI later)
    session_row.last_activity_at = now
    db.commit()

    return user


def revoke_session(db: DbSession, *, jwt_token: str) -> bool:
    """Invalidate a session — used by logout.

    Returns True if a session was deleted, False if no matching session
    was found (already expired, or never existed).

    We look up by the session hash extracted from the JWT and delete the
    row. Without the row, future requests with this JWT will fail at
    `get_user_from_jwt`.
    """
    payload = security.decode_access_token(jwt_token)
    if payload is None:
        return False

    session_token = payload.get("sid")
    if not session_token:
        return False

    token_hash = security.hash_token(session_token)
    session_row = (
        db.query(UserSession)
        .filter(UserSession.token_hash == token_hash)
        .first()
    )

    if session_row is None:
        return False

    db.delete(session_row)
    db.commit()
    return True


# ============================================================
# Internal helpers
# ============================================================

# A fake hash used to equalize response time when an email doesn't exist.
# Generated once at module import; we don't care what password it matches.
# (It's a valid argon2id hash of the string "dummy" — won't match real passwords.)
_DUMMY_HASH = security.hash_password("dummy-password-for-timing-attack-prevention")
