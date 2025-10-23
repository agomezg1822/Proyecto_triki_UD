# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./triki.db"

# Crear engine
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# Sesión local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para heredar modelos
Base = declarative_base()


# Dependencia para FastAPI (inyectar sesión)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()