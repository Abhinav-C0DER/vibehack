import pytest
from app.sockets.connection import connect, disconnect, join_room
from app.sockets.chat import send_message, whisper, heartbeat
from app.db.models import User
from app.core.config import settings
from app.redis_cache.connection import redis_client
from jose import jwt
from sqlmodel import Session, select
from unittest.mock import AsyncMock

pytestmark = pytest.mark.asyncio

async def test_socket_connect(sio_mock):
    # Connect should run without errors
    await connect("test_sid", {})
    # No major side effects, just prints/logging

async def test_socket_join_room_success(client, sio_mock, db_session: Session):
    # Setup permanent user in database
    db_user = User(username="socket_real_user", hashed_password="hashedpassword123")
    db_session.add(db_user)
    db_session.commit()

    # Generate valid token
    token = jwt.encode({"sub": "socket_real_user"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    # Invoke join_room handler
    result = await join_room("test_sid", {
        "room_name": "Lobby",
        "category": "General",
        "token": token
    })

    assert result["status"] == "joined"
    ghost_name = result["username"]
    assert len(ghost_name) > 0

    # Verify Redis pointers established
    assert redis_client.get(f"ghost_pointer:{ghost_name}") == "socket_real_user"
    assert redis_client.get(f"ghost_to_sid:{ghost_name}") == "test_sid"
    assert redis_client.sismember("room_users:Lobby", ghost_name)

    # Verify save_session was called
    sio_mock.save_session.assert_called_with("test_sid", {
        "room": "Lobby",
        "username": ghost_name,
        "real_username": "socket_real_user"
    })

    # Verify broadcast events
    sio_mock.enter_room.assert_called_with("test_sid", "Lobby")
    sio_mock.emit.assert_any_call("room_users", {"users": [ghost_name]}, room="Lobby")
    sio_mock.emit.assert_any_call("system_message", {"msg": f"Welcome to Lobby, {ghost_name}."}, to="test_sid")

async def test_socket_join_room_missing_token():
    result = await join_room("test_sid", {"room_name": "Lobby"})
    assert result["status"] == "rejected"
    assert "token missing" in result["error"].lower()

async def test_socket_join_room_invalid_token():
    result = await join_room("test_sid", {"room_name": "Lobby", "token": "invalid-token-123"})
    assert result["status"] == "rejected"
    assert "expired or corrupted" in result["error"].lower()

async def test_socket_join_room_banned_user(client, sio_mock, db_session: Session):
    # Setup banned user
    db_user = User(username="banned_socket_user", hashed_password="password", is_banned=True)
    db_session.add(db_user)
    db_session.commit()

    token = jwt.encode({"sub": "banned_socket_user"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    result = await join_room("test_sid", {
        "room_name": "Lobby",
        "token": token
    })
    assert result["status"] == "rejected"
    assert "exorcised" in result["error"].lower()

async def test_socket_disconnect(sio_mock):
    # Setup mock session
    sio_mock.get_session.return_value = {
        "room": "Lobby",
        "username": "GhostlySpook"
    }

    # Setup Redis keys
    redis_client.set("ghost_to_sid:GhostlySpook", "test_sid")
    redis_client.sadd("room_users:Lobby", "GhostlySpook")
    # Add another user so the room doesn't vanish
    redis_client.sadd("room_users:Lobby", "OtherGhost")
    redis_client.hset("room:Lobby", mapping={"category": "General", "user_count": 2})

    # Invoke disconnect
    await disconnect("test_sid")

    # Verify Redis cleanups
    assert not redis_client.exists("ghost_to_sid:GhostlySpook")
    assert not redis_client.sismember("room_users:Lobby", "GhostlySpook")
    assert int(redis_client.hget("room:Lobby", "user_count")) == 1

    # Verify leave room and broadcasts
    sio_mock.leave_room.assert_called_with("test_sid", "Lobby")
    sio_mock.emit.assert_any_call("room_users", {"users": ["OtherGhost"]}, room="Lobby")
    sio_mock.emit.assert_any_call("system_message", {"msg": "GhostlySpook faded away."}, room="Lobby")

async def test_socket_send_message(sio_mock):
    sio_mock.get_session.return_value = {
        "room": "Lobby",
        "username": "ChattyGhost"
    }

    await send_message("test_sid", {"message": "Hello from the void!"})

    sio_mock.emit.assert_called_with(
        "receive_message",
        {
            "sender": "ChattyGhost",
            "message": "Hello from the void!",
            "is_whisper": False
        },
        room="Lobby"
    )

async def test_socket_whisper(sio_mock):
    sio_mock.get_session.return_value = {
        "username": "WhisperingGhost"
    }

    await whisper("test_sid", {
        "target_sid": "receiver_sid_123",
        "message": "A secret whisper..."
    })

    sio_mock.emit.assert_called_with(
        "receive_message",
        {
            "sender": "WhisperingGhost",
            "message": "A secret whisper...",
            "is_whisper": True
        },
        to="receiver_sid_123"
    )

async def test_socket_heartbeat_success(sio_mock, db_session: Session):
    # Setup database user
    db_user = User(username="heartbeat_user", hashed_password="password", auth_points=10)
    db_session.add(db_user)
    db_session.commit()

    # Session mock
    sio_mock.get_session.return_value = {
        "room": "Lobby",
        "username": "HeartbeatGhost"
    }
    
    # Redis pointer mapping ghost name to real username
    redis_client.set("ghost_pointer:HeartbeatGhost", "heartbeat_user")

    # Invoke heartbeat
    await heartbeat("test_sid")

    # Verify point incremented in DB
    db_session.expire_all()
    user = db_session.exec(select(User).where(User.username == "heartbeat_user")).first()
    assert user.auth_points == 11

async def test_socket_heartbeat_banned_user_gets_disconnected(sio_mock, db_session: Session):
    db_user = User(username="banned_heartbeat_user", hashed_password="password", is_banned=True)
    db_session.add(db_user)
    db_session.commit()

    sio_mock.get_session.return_value = {
        "room": "Lobby",
        "username": "BannedHeartbeatGhost"
    }
    redis_client.set("ghost_pointer:BannedHeartbeatGhost", "banned_heartbeat_user")

    await heartbeat("test_sid")

    # Banned user must be disconnected immediately!
    sio_mock.disconnect.assert_called_with("test_sid")
