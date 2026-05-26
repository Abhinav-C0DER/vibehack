from app.sockets.server import sio
from app.redis_cache.manager import RoomManager
from app.utils.identity import generate_ghost_name
from app.db.session import Session, engine
from app.db.models import User
from sqlmodel import select
from app.redis_cache.connection import redis_client
from app.core.config import settings
from jose import jwt, JWTError

# --- 1. Connection & Disconnection ---

@sio.event
async def connect(sid, environ):
    print(f"👻 Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"👋 Client disconnected: {sid}")
    
    # Retrieve the user's session data to know which room they were in
    session = await sio.get_session(sid)
    if session and "room" in session:
        room_name = session["room"]
        username = session["username"]
        
        # Delete ghost to SID mapping
        redis_client.delete(f"ghost_to_sid:{username}")
        
        # 1. Leave the Socket.IO room
        await sio.leave_room(sid, room_name)
        
        # 2. Tell Redis they left. If it returns True, the room vanished!
        vanished = RoomManager.leave_room(room_name)
        
        if vanished:
            print(f"💥 Room '{room_name}' vanished into the void.")
            redis_client.delete(f"room_users:{room_name}")
        else:
            # Remove from room users set in Redis
            redis_client.srem(f"room_users:{room_name}", username)
            # Broadcast updated users list
            active_users = list(redis_client.smembers(f"room_users:{room_name}"))
            await sio.emit("room_users", {"users": active_users}, room=room_name)
            
            # Tell the remaining people in the room that someone left
            await sio.emit("system_message", {"msg": f"{username} faded away."}, room=room_name)

# --- 2. Secure Room Management ---

@sio.event
async def join_room(sid, data):
    """Triggered when a user clicks a room on the dashboard. Requires JWT token."""
    room_name = data.get("room_name")
    category = data.get("category", "General")
    token = data.get("token")
    
    if not token:
        return {"status": "rejected", "error": "Authentication token missing from request waves."}
    
    # Decode and validate JWT token
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        permanent_username = payload.get("sub")
        if not permanent_username:
            return {"status": "rejected", "error": "Invalid token signature in the void."}
    except JWTError:
        return {"status": "rejected", "error": "Expired or corrupted authentication frequency."}
    
    # Verify underlying account status
    with Session(engine) as db:
        statement = select(User).where(User.username == permanent_username)
        user = db.exec(statement).first()
        if not user:
            return {"status": "rejected", "error": "Identity anchor has faded from persistent memory."}
        if user.is_banned:
            return {"status": "rejected", "error": "This identity has been exorcised from the void (banned)."}
    
    # 1. Generate their unique ephemeral ghost name
    ghost_name = generate_ghost_name()
    
    # 2. Establish Redis pointers (24-hour expiration)
    redis_client.set(f"ghost_pointer:{ghost_name}", permanent_username, ex=86400)
    redis_client.set(f"ghost_to_sid:{ghost_name}", sid, ex=86400)
    
    # 3. Save secure session state
    await sio.save_session(sid, {
        "room": room_name, 
        "username": ghost_name,
        "real_username": permanent_username
    })
    
    # 4. Join the Socket.IO room & track active users
    await sio.enter_room(sid, room_name)
    RoomManager.join_room(room_name, category)
    
    redis_client.sadd(f"room_users:{room_name}", ghost_name)
    redis_client.expire(f"room_users:{room_name}", 86400)
    
    # 5. Broadcast updated user list and welcoming announcements
    active_users = list(redis_client.smembers(f"room_users:{room_name}"))
    await sio.emit("room_users", {"users": active_users}, room=room_name)
    
    await sio.emit("system_message", {"msg": f"Welcome to {room_name}, {ghost_name}."}, to=sid)
    await sio.emit("system_message", {"msg": f"{ghost_name} manifested in the room."}, room=room_name, skip_sid=sid)
    
    return {"status": "joined", "username": ghost_name, "sid": sid}
