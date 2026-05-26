import pytest
from app.db.models import User
from sqlmodel import Session, select

def test_register_user_success(client, db_session: Session):
    response = client.post(
        "/api/auth/register",
        json={"username": "testghost", "password": "supersecretpassword"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testghost"
    assert "password" not in data
    assert data["auth_points"] == 0
    assert data["bio"] == "A mysterious ghost..."

    # Verify user exists in the DB
    statement = select(User).where(User.username == "testghost")
    user = db_session.exec(statement).first()
    assert user is not None
    assert user.username == "testghost"
    assert user.auth_points == 0

def test_register_duplicate_username_fails(client):
    # Register first user
    client.post(
        "/api/auth/register",
        json={"username": "duplicate_ghost", "password": "password123"}
    )
    # Register second user with same username
    response = client.post(
        "/api/auth/register",
        json={"username": "duplicate_ghost", "password": "password456"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "This ghost name is already taken. Try another."

def test_login_user_success(client):
    # Register user first
    client.post(
        "/api/auth/register",
        json={"username": "login_ghost", "password": "secretpassword"}
    )

    # Perform login
    response = client.post(
        "/api/auth/login",
        data={"username": "login_ghost", "password": "secretpassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials_fails(client):
    # Register user first
    client.post(
        "/api/auth/register",
        json={"username": "wrong_ghost", "password": "secretpassword"}
    )

    # Wrong password
    response_wrong_pass = client.post(
        "/api/auth/login",
        data={"username": "wrong_ghost", "password": "wrongpassword"}
    )
    assert response_wrong_pass.status_code == 401
    assert response_wrong_pass.json()["detail"] == "Incorrect username or password"

    # Non-existent user
    response_no_user = client.post(
        "/api/auth/login",
        data={"username": "nonexistent_ghost", "password": "password"}
    )
    assert response_no_user.status_code == 401
    assert response_no_user.json()["detail"] == "Incorrect username or password"

def test_login_banned_user_fails(client, db_session: Session):
    # Register user
    client.post(
        "/api/auth/register",
        json={"username": "bad_ghost", "password": "secretpassword"}
    )

    # Ban the user directly in DB
    statement = select(User).where(User.username == "bad_ghost")
    user = db_session.exec(statement).first()
    user.is_banned = True
    db_session.add(user)
    db_session.commit()

    # Attempt login
    response = client.post(
        "/api/auth/login",
        data={"username": "bad_ghost", "password": "secretpassword"}
    )
    assert response.status_code == 403
    assert "exorcised" in response.json()["detail"]
