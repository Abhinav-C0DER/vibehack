import os
import sys
from unittest.mock import AsyncMock, MagicMock

# 1. Force testing environment variables before importing any app modules
os.environ["DATABASE_URL"] = "sqlite:///./test_vibehack.db"
os.environ["SECRET_KEY"] = "test_secret_key_vibehack_super_secure_random"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"

import pytest
import redis
from sqlmodel import SQLModel, Session, create_engine
from fastapi.testclient import TestClient

# 2. Setup isolated Redis DB 15 client and patch the connection module
test_redis = redis.Redis(host="localhost", port=6379, db=15, decode_responses=True)
import app.redis_cache.connection
app.redis_cache.connection.redis_client = test_redis

# 3. Patch Socket.io server to mock real-time broadcasts
mock_sio = MagicMock()
mock_sio.event = lambda func: func
mock_sio.on = lambda *args, **kwargs: lambda func: func
mock_sio.emit = AsyncMock()
mock_sio.disconnect = AsyncMock()
mock_sio.save_session = AsyncMock()
mock_sio.get_session = AsyncMock()
mock_sio.enter_room = AsyncMock()
mock_sio.leave_room = AsyncMock()

import app.sockets.server
app.sockets.server.sio = mock_sio
# Repatch in other modules that import sio directly
import app.sockets.connection
app.sockets.connection.sio = mock_sio
import app.sockets.chat
app.sockets.chat.sio = mock_sio
import app.api.users
app.api.users.sio = mock_sio

# Now we can import the engine and main app
from app.db.session import engine, init_db
from app.main import app as fastapi_app

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Initializes the database schema once for the test session and cleans up after."""
    # Ensure any residual test DB is removed
    if os.path.exists("test_vibehack.db"):
        try:
            os.remove("test_vibehack.db")
        except PermissionError:
            pass

    # Initialize tables
    init_db()
    
    yield
    
    # Teardown: close engine connections and delete file
    engine.dispose()
    if os.path.exists("test_vibehack.db"):
        try:
            os.remove("test_vibehack.db")
        except PermissionError:
            pass

@pytest.fixture(autouse=True)
def clean_redis():
    """Flushes the isolated Redis test database before each test run."""
    test_redis.flushdb()
    yield
    test_redis.flushdb()

@pytest.fixture
def db_session():
    """Provides a clean SQLModel database session per test with rollback capability."""
    with Session(engine) as session:
        yield session
        # Truncate tables for fresh state
        session.rollback()
        for table in reversed(SQLModel.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()

@pytest.fixture
def client(db_session):
    """FastAPI TestClient fixture with overridden DB dependency."""
    from app.db.session import get_session
    
    def override_get_session():
        yield db_session
        
    fastapi_app.dependency_overrides[get_session] = override_get_session
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()

@pytest.fixture
def sio_mock():
    """Provides the mocked Socket.io AsyncServer instance and resets its calls."""
    mock_sio.emit.reset_mock()
    mock_sio.disconnect.reset_mock()
    mock_sio.save_session.reset_mock()
    mock_sio.get_session.reset_mock()
    mock_sio.enter_room.reset_mock()
    mock_sio.leave_room.reset_mock()
    return mock_sio
