from sqlmodel import create_engine, Session, SQLModel
from app.core.config import settings

db_url = settings.DATABASE_URL

# Only pass check_same_thread argument if using SQLite
if db_url.startswith("sqlite"):
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
else:
    engine = create_engine(db_url)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
