from sqlalchemy import create_engine, URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

SQLALCHEMY_DATABASE_URL = URL.create(
    drivername="postgresql+psycopg",
    username=settings.database_username,
    password=settings.database_password,
    host=settings.database_hostname,
    port=settings.database_port,
    database=settings.database_name,
)

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()