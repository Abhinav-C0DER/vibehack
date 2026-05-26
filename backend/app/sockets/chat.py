from app.sockets.server import sio
from app.redis_cache.manager import RoomManager
from app.utils.identity import generate_ghost_name
from app.db.session import Session, engine
from app.db.models import User
from sqlmodel import select
from app.redis_cache.connection import redis_client

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


# --- 2. Room Management ---

@sio.event
async def join_room(sid, data):
    """Triggered when a user clicks a room on the dashboard."""
    room_name = data.get("room_name")
    category = data.get("category", "General")
    
    # NEW: Get the permanent username from the frontend's request
    permanent_username = data.get("permanent_username") 
    
    # Check if the user is banned in Postgres
    if permanent_username:
        with Session(engine) as db:
            statement = select(User).where(User.username == permanent_username)
            user = db.exec(statement).first()
            if user and user.is_banned:
                return {"status": "rejected", "error": "This identity has been exorcised from the void (banned)."}
    
    # 1. Generate their burned username
    ghost_name = generate_ghost_name()
    
    # ---> NEW: Create the pointer in Redis (Expires in 24 hours / 86400 seconds) <---
    if permanent_username:
        redis_client.set(f"ghost_pointer:{ghost_name}", permanent_username, ex=86400)
    
    # Store the mapping from ghost name to Socket SID in Redis
    redis_client.set(f"ghost_to_sid:{ghost_name}", sid, ex=86400)
    
    # 2. Save state to this specific connection session
    await sio.save_session(sid, {"room": room_name, "username": ghost_name})
    
    # 3. Add to Socket.IO room and Redis
    await sio.enter_room(sid, room_name)
    RoomManager.join_room(room_name, category)
    
    # Track room users in Redis
    redis_client.sadd(f"room_users:{room_name}", ghost_name)
    redis_client.expire(f"room_users:{room_name}", 86400)
    
    # Broadcast updated users list
    active_users = list(redis_client.smembers(f"room_users:{room_name}"))
    await sio.emit("room_users", {"users": active_users}, room=room_name)
    
    # 4. Welcome the user and alert the room
    await sio.emit("system_message", {"msg": f"Welcome to {room_name}, {ghost_name}."}, to=sid)
    await sio.emit("system_message", {"msg": f"{ghost_name} manifested in the room."}, room=room_name, skip_sid=sid)
    
    # Send back the generated identity to the user's frontend
    return {"status": "joined", "username": ghost_name, "sid": sid}

# --- 3. Messaging & Whispering ---

@sio.event
async def send_message(sid, data):
    print(f"\n--- 🚀 NEW MESSAGE RECEIVED ---")
    print(f"From SID: {sid}")
    print(f"Payload: {data}")
    
    # 1. Check if the server remembers who this user is
    session = await sio.get_session(sid)
    print(f"Session Data: {session}")
    
    if not session:
        print("❌ ERROR: No session found! The message is being dropped.")
        return
        
    room_name = session.get("room")
    username = session.get("username")
    message = data.get("message")
    
    print(f"📢 Broadcasting as '{username}' to room '{room_name}': {message}")
    
    # 2. Attempt to broadcast
    try:
        await sio.emit("receive_message", {
            "sender": username,
            "message": message,
            "is_whisper": False
        }, room=room_name)
        print("✅ Broadcast successful!")
    except Exception as e:
        print(f"❌ ERROR during broadcast: {e}")
    print("------------------------------\n")

@sio.event
async def whisper(sid, data):
    """The private sub-conversation feature."""
    session = await sio.get_session(sid)
    target_sid = data.get("target_sid") # The frontend must send the SID of the person they are clicking on
    message = data.get("message")
    
    if session and target_sid:
        sender_name = session["username"]
        # Send ONLY to the target user
        await sio.emit("receive_message", {
            "sender": sender_name,
            "message": message,
            "is_whisper": True
        }, to=target_sid)

@sio.event
async def heartbeat(sid):
    session = await sio.get_session(sid)
    if not session:
        return
        
    # Every time the frontend 'pings', increment points in the DB
    # (In production, you'd only do this every 5 or 10 pings to save resources)
   
    
    room = session.get("room")
    # We need the real username from our Redis pointer!
    ghost_name = session.get("username")
    real_username = redis_client.get(f"ghost_pointer:{ghost_name}")
    
    if real_username:
        with Session(engine) as db:
            statement = select(User).where(User.username == real_username)
            user = db.exec(statement).first()
            if user:
                if user.is_banned:
                    # Exorcise them immediately!
                    await sio.disconnect(sid)
                    return
                user.auth_points += 1
                db.add(user)
                db.commit()

