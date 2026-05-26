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
async def connect(sid, environ, auth=None):
    print(f"👻 Client connected: {sid}")
    return True

@sio.event
async def disconnect(sid):
    print(f"👋 Client disconnected: {sid}")
    
    # Retrieve the user's session data securely
    session = await sio.get_session(sid)
    if not session or "room" not in session:
        return
        
    room_name = session["room"]
    username = session["username"]
    
    # Delete ghost to SID mapping securely
    redis_client.delete(f"ghost_to_sid:{username}")
    
    # 1. Leave the Socket.IO core broadcast room
    try:
        await sio.leave_room(sid, room_name)
    except Exception:
        pass
    
    # 2. Remove the specific user from the Redis set first
    redis_client.srem(f"room_users:{room_name}", username)
    
    # 3. Tell RoomManager they left on EVERY disconnect so internal counters decrement correctly
    vanished = False
    try:
        vanished = RoomManager.leave_room(room_name)
    except Exception as e:
        print(f"⚠️ RoomManager tracking error: {e}")
    
    # 4. Check if the room has completely emptied out
    remaining_count = redis_client.scard(f"room_users:{room_name}")
    
    if vanished or remaining_count <= 0:
        print(f"💥 Room '{room_name}' vanished into the void (0 active ghosts remaining).")
        redis_client.delete(f"room_users:{room_name}")
    else:
        # Broadcast updated users list to the ghosts still inside the room
        active_users = list(redis_client.smembers(f"room_users:{room_name}"))
        active_users = [u.decode('utf-8') if isinstance(u, bytes) else u for u in active_users]
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
    
# 5. Broadcast updated user list and welcoming announcements securely
    try:
        active_users = list(redis_client.smembers(f"room_users:{room_name}"))
        # Force decode items to string if Redis returns raw bytes
        active_users = [u.decode('utf-8') if isinstance(u, bytes) else u for u in active_users]
        
        await sio.emit("room_users", {"users": active_users}, room=room_name)
        
        await sio.emit("system_message", {"msg": f"Welcome to {room_name}, {ghost_name}."}, to=sid)
        await sio.emit("system_message", {"msg": f"{ghost_name} manifested in the room."}, room=room_name, skip_sid=sid)
    except Exception as e:
        print(f"⚠️ Warning during join broadcast chain: {e}")
    
    return {"status": "joined", "username": ghost_name, "sid": sid}
