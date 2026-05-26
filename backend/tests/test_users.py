import pytest
from app.db.models import User
from app.redis_cache.connection import redis_client
from sqlmodel import Session, select
from unittest.mock import AsyncMock

def _get_auth_headers(client, username, password="password123"):
    client.post(
        "/api/auth/register",
        json={"username": username, "password": password}
    )
    login_res = client.post(
        "/api/auth/login",
        data={"username": username, "password": password}
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_get_my_dashboard(client):
    headers = _get_auth_headers(client, "dash_ghost")
    response = client.get("/api/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "dash_ghost"
    assert data["auth_points"] == 0
    assert data["bio"] == "A mysterious ghost..."

def test_get_my_dashboard_unauthorized(client):
    response = client.get("/api/users/me")
    assert response.status_code == 401

def test_update_bio(client, db_session: Session):
    headers = _get_auth_headers(client, "bio_ghost")
    
    # Update bio
    response = client.put(
        "/api/users/me",
        json={"bio": "I am into Python development and hacking space!"},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["bio"] == "I am into Python development and hacking space!"

    # Verify db was updated
    statement = select(User).where(User.username == "bio_ghost")
    user = db_session.exec(statement).first()
    assert user.bio == "I am into Python development and hacking space!"

def test_get_ghost_profile_success(client):
    headers = _get_auth_headers(client, "real_ghost_owner")
    
    # Set ghost name pointers in Redis
    redis_client.set("ghost_pointer:WhisperingShadow", "real_ghost_owner")
    redis_client.set("ghost_to_sid:WhisperingShadow", "test_socket_sid_123")

    response = client.get("/api/users/ghost/WhisperingShadow", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["ghost_name"] == "WhisperingShadow"
    assert data["bio"] == "A mysterious ghost..."
    assert data["auth_points"] == 0
    assert data["sid"] == "test_socket_sid_123"

def test_get_ghost_profile_not_found(client):
    headers = _get_auth_headers(client, "some_viewer")
    response = client.get("/api/users/ghost/NonexistentGhost", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Ghost vanished or does not exist."

def test_gift_authenticity_point_success(client, db_session: Session):
    # Setup caller
    caller_headers = _get_auth_headers(client, "caller_ghost")
    
    # Setup target user
    client.post("/api/auth/register", json={"username": "target_ghost", "password": "password"})
    
    # Set target's ghost pointer in Redis
    redis_client.set("ghost_pointer:TargetGhostName", "target_ghost")

    # Gift point
    response = client.post("/api/users/gift/TargetGhostName", headers=caller_headers)
    assert response.status_code == 200
    assert "Successfully gifted" in response.json()["message"]

    # Verify points incremented in DB
    statement = select(User).where(User.username == "target_ghost")
    target = db_session.exec(statement).first()
    assert target.auth_points == 1

def test_gift_authenticity_point_to_self_fails(client):
    headers = _get_auth_headers(client, "self_gifter")
    redis_client.set("ghost_pointer:SelfGhostName", "self_gifter")

    # Attempt gifting to self
    response = client.post("/api/users/gift/SelfGhostName", headers=headers)
    assert response.status_code == 400
    assert response.json()["detail"] == "You cannot gift points to yourself!"

def test_gift_authenticity_point_not_found(client):
    headers = _get_auth_headers(client, "some_gifter")
    response = client.post("/api/users/gift/NonexistentGhost", headers=headers)
    assert response.status_code == 404

def test_report_ghost_flow(client, db_session: Session, sio_mock):
    # Setup caller, target 1, target 2
    reporter1_headers = _get_auth_headers(client, "reporter_one")
    reporter2_headers = _get_auth_headers(client, "reporter_two")
    reporter3_headers = _get_auth_headers(client, "reporter_three")
    
    client.post("/api/auth/register", json={"username": "spammer", "password": "password"})
    redis_client.set("ghost_pointer:SpammyGhost", "spammer")
    redis_client.set("ghost_to_sid:SpammyGhost", "spammer_sid")

    # Verify initial points are 0
    statement = select(User).where(User.username == "spammer")
    target = db_session.exec(statement).first()
    assert target.auth_points == 0

    # 1. Report 1 (by reporter_one)
    res1 = client.post("/api/users/report/SpammyGhost?room_name=Lobby", headers=reporter1_headers)
    assert res1.status_code == 200
    assert res1.json()["reports"] == 1
    assert res1.json()["banned"] is False
    
    # Assert system message was emitted to Lobby room
    sio_mock.emit.assert_called_with(
        "system_message",
        {"msg": "⚠️ Ghost SpammyGhost was reported by another ghost (1/3 flags)."},
        room="Lobby"
    )

    # Verify -5 points in DB
    db_session.expire_all()
    target = db_session.exec(statement).first()
    assert target.auth_points == -5

    # Test anti-spam (reporter_one reports again)
    res_spam = client.post("/api/users/report/SpammyGhost?room_name=Lobby", headers=reporter1_headers)
    assert res_spam.status_code == 400
    assert "already reported" in res_spam.json()["detail"]

    # 2. Report 2 (by reporter_two)
    sio_mock.emit.reset_mock()
    res2 = client.post("/api/users/report/SpammyGhost?room_name=Lobby", headers=reporter2_headers)
    assert res2.status_code == 200
    assert res2.json()["reports"] == 2
    assert res2.json()["banned"] is False
    
    sio_mock.emit.assert_called_with(
        "system_message",
        {"msg": "⚠️ Ghost SpammyGhost was reported by another ghost (2/3 flags)."},
        room="Lobby"
    )

    db_session.expire_all()
    target = db_session.exec(statement).first()
    assert target.auth_points == -10

    # 3. Report 3 (by reporter_three -> should trigger ban!)
    sio_mock.emit.reset_mock()
    res3 = client.post("/api/users/report/SpammyGhost?room_name=Lobby", headers=reporter3_headers)
    assert res3.status_code == 200
    assert res3.json()["reports"] == 3
    assert res3.json()["banned"] is True
    
    # Verify ban broadcast and socket disconnect
    sio_mock.emit.assert_called_with(
        "system_message",
        {"msg": "⚡ Ghost SpammyGhost has been EXORCISED from the void (3/3 Reports)."},
        room="Lobby"
    )
    sio_mock.disconnect.assert_called_with("spammer_sid")

    # Verify banned status and extra -10 slash penalty (total -25 points)
    db_session.expire_all()
    target = db_session.exec(statement).first()
    assert target.is_banned is True
    assert target.auth_points == -25
