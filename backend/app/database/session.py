import os
import socket
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config.config import settings

# Determine which DB to use
db_url = settings.DATABASE_URL
connect_args = {}

# Fallback to local SQLite if 'db' host is not resolvable or if we are outside Docker
if "@db:" in db_url or "://db:" in db_url or "@db" in db_url:
    try:
        socket.gethostbyname('db')
    except socket.gaierror:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sqlite_path = os.path.join(base_dir, "test.db")
        db_url = f"sqlite:///{sqlite_path.replace('\\', '/')}"
        print(f"Postgres host 'db' not resolvable. Falling back to local SQLite at: {db_url}")

if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(db_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
