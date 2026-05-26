import pytest
from app.redis_cache.manager import RoomManager
from app.redis_cache.connection import redis_client

def _get_auth_headers(client, username, bio=None):
    client.post(
        "/api/auth/register",
        json={"username": username, "password": "password123"}
    )
    if bio:
        login_res = client.post(
            "/api/auth/login",
            data={"username": username, "password": "password123"}
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        client.put("/api/users/me", json={"bio": bio}, headers=headers)
        return headers
    else:
        login_res = client.post(
            "/api/auth/login",
            data={"username": username, "password": "password123"}
        )
        token = login_res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

def test_get_trending_rooms_empty(client):
    response = client.get("/api/rooms/trending")
    assert response.status_code == 200
    assert response.json()["trending_rooms"] == []

def test_get_trending_rooms_with_data(client):
    # Set up some rooms in Redis
    RoomManager.join_room("python-dev", "Coding")
    RoomManager.join_room("gaming-lounge", "Gaming")

    response = client.get("/api/rooms/trending")
    assert response.status_code == 200
    rooms = response.json()["trending_rooms"]
    assert len(rooms) == 2
    # Verify room names are present
    names = [r["room_name"] for r in rooms]
    assert "python-dev" in names
    assert "gaming-lounge" in names

def test_get_recommended_rooms(client):
    # Setup user with "gaming" and "chill" in their bio
    headers = _get_auth_headers(
        client,
        "gamer_ghost",
        bio="Hello! I love gaming, playing anime games, and just having a chill time."
    )

    # Setup rooms in Redis
    RoomManager.join_room("gaming-hub", "Gaming")       # Matches "gaming" (name and category)
    RoomManager.join_room("chill-zone", "Hangout")      # Matches "chill"
    RoomManager.join_room("rust-coding", "Development") # No match
    RoomManager.join_room("anime-club", "Anime")        # Matches "anime" (but anime is not in KEYWORDS? Wait, "anime" IS in KEYWORDS list in rooms.py!)

    response = client.get("/api/rooms/recommended", headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    recommended = data["recommended_rooms"]
    other = data["other_rooms"]
    matched = data["matched_keywords"]

    # Verify matched keywords detected in bio
    assert "gaming" in matched
    assert "chill" in matched
    assert "anime" in matched
    assert "rust" not in matched

    # Verify recommendations flag is correct
    recommended_names = [r["room_name"] for r in recommended]
    other_names = [r["room_name"] for r in other]

    assert "gaming-hub" in recommended_names
    assert "chill-zone" in recommended_names
    assert "anime-club" in recommended_names
    assert "rust-coding" in other_names

    # Recommended rooms should have is_recommended == True
    for r in recommended:
        assert r["is_recommended"] is True
        assert r["match_score"] > 0

    # Other rooms should have is_recommended == False
    for r in other:
        assert r["is_recommended"] is False
        assert r["match_score"] == 0

def test_get_recommended_rooms_fallback(client):
    # Setup user with empty bio (no keywords)
    headers = _get_auth_headers(client, "blank_ghost", bio="")

    # Setup rooms
    RoomManager.join_room("random-chat", "General") # Active with 1 user

    response = client.get("/api/rooms/recommended", headers=headers)
    assert response.status_code == 200
    data = response.json()

    # If bio matches nothing, active rooms (user_count > 0) are still recommended as fallback
    recommended = data["recommended_rooms"]
    assert len(recommended) == 1
    assert recommended[0]["room_name"] == "random-chat"
    assert recommended[0]["is_recommended"] is True
    assert recommended[0]["match_score"] == 0
