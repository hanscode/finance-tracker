"""
Database connection and session management.

💡 CONCEPT: SQLAlchemy Engine vs Session
   In your Techdegree projects you used SQLAlchemy like this:
       engine = create_engine('sqlite:///books.db')
       Session = sessionmaker(bind=engine)
       session = Session()

   Here we do the same but with two improvements:
   1. WAL mode — allows multiple reads to happen at the same time
   2. Dependency Injection — FastAPI injects the session automatically into each request

💡 CONCEPT: WAL (Write-Ahead Logging)
   By default, SQLite locks the ENTIRE database when someone writes.
   With WAL mode, writes go to a separate file (write-ahead log)
   and reads can continue without blocking. This is what
   Campfire and Writebook from 37signals use.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# check_same_thread=False is needed because FastAPI uses multiple threads
# but SQLite by default only allows access from the thread that created it
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=settings.DEBUG,  # If DEBUG=True, prints all SQL queries
)


# Enable WAL mode and immediate transaction mode on connect
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Configure SQLite for better concurrency on each new connection."""
    cursor = dbapi_connection.cursor()
    # WAL mode: allows concurrent reads during writes
    cursor.execute("PRAGMA journal_mode=WAL")
    # Foreign keys: SQLite doesn't enable them by default (!)
    cursor.execute("PRAGMA foreign_keys=ON")
    # Busy timeout: wait 5 seconds if the DB is locked before failing
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


# Session factory — creates database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Base class for all models (you'll see this in Phase 2)
class Base(DeclarativeBase):
    pass


def get_db():
    """
    Dependency that FastAPI injects into each endpoint.

    💡 CONCEPT: Dependency Injection
       In Flask you did: session = Session() at the top of the file.
       In FastAPI, each endpoint declares that it NEEDS a session:

           @router.get("/items")
           def get_items(db: Session = Depends(get_db)):
               ...

       FastAPI automatically:
       1. Calls get_db()
       2. Gives you the session (db)
       3. When the endpoint finishes, closes the session (finally)

       This prevents memory leaks and open connections.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
