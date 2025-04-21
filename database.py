from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from forest_app.config.settings import settings

SQLALCHEMY_DATABASE_URL = settings.db_connection_string

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
