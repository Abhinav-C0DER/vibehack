import pytest
import time
from app.redis_cache.manager import RoomManager
from app.redis_cache.connection import redis_client

def test_join_room_initialization():
    room_name = "test-redis-room"
    category = "General"
    
    # Verify not existing yet
    assert not redis_client.exists(f"room:{room_name}")

    # Join room
    RoomManager.join_room(room_name, category)
    
    # Verify creation and state
    room_key = f"room:{room_name}"
    assert redis_client.exists(room_key)
    
    data = redis_client.hgetall(room_key)
    assert data["category"] == category
    assert int(data["user_count"]) == 1
    assert "created_at" in data

def test_join_room_increment():
    room_name = "test-redis-room"
    RoomManager.join_room(room_name, "General")
    RoomManager.join_room(room_name, "General")

    room_key = f"room:{room_name}"
    user_count = int(redis_client.hget(room_key, "user_count"))
    assert user_count == 2

def test_leave_room_decrement():
    room_name = "test-redis-room"
    RoomManager.join_room(room_name, "General")
    RoomManager.join_room(room_name, "General")

    # Leave 1 user
    vanished = RoomManager.leave_room(room_name)
    assert vanished is False

    room_key = f"room:{room_name}"
    assert redis_client.exists(room_key)
    user_count = int(redis_client.hget(room_key, "user_count"))
    assert user_count == 1

def test_leave_room_vanishing_act():
    room_name = "test-redis-room"
    RoomManager.join_room(room_name, "General")

    # Leave the only user (should trigger the Vanishing Act!)
    vanished = RoomManager.leave_room(room_name)
    assert vanished is True

    # Verify key deleted
    room_key = f"room:{room_name}"
    assert not redis_client.exists(room_key)

def test_get_trending_rooms_ranking():
    # Setup multiple rooms with different popularity/creation times
    # Room 1: High user count
    RoomManager.join_room("popular-room", "General")
    RoomManager.join_room("popular-room", "General")
    RoomManager.join_room("popular-room", "General") # user_count = 3
    
    # Room 2: Medium user count
    RoomManager.join_room("medium-room", "General")
    RoomManager.join_room("medium-room", "General") # user_count = 2

    # Room 3: Low user count
    RoomManager.join_room("quiet-room", "General") # user_count = 1

    trending = RoomManager.get_trending_rooms()
    assert len(trending) == 3
    
    # Should be sorted popular -> medium -> quiet
    assert trending[0]["room_name"] == "popular-room"
    assert trending[1]["room_name"] == "medium-room"
    assert trending[2]["room_name"] == "quiet-room"

    assert trending[0]["user_count"] == 3
    assert trending[1]["user_count"] == 2
    assert trending[2]["user_count"] == 1
