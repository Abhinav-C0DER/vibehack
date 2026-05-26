from app.sockets.server import sio
from app.db.session import Session, engine
from app.db.models import User
from sqlmodel import select
from app.redis_cache.connection import redis_client

# --- 1. Messaging & Whispering ---

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
        
    ghost_name = session.get("username")
    if not ghost_name:
        return

    # Fetch the pointer
    raw_username = redis_client.get(f"ghost_pointer:{ghost_name}")
    if not raw_username:
        return
        
    # Safeguard: Force decode to string if it somehow arrives as raw bytes
    real_username = raw_username.decode('utf-8') if isinstance(raw_username, bytes) else raw_username
    
    with Session(engine) as db:
        statement = select(User).where(User.username == real_username)
        user = db.exec(statement).first()
        
        # FIX: Ensure user object exists before validating properties!
        if user:
            if user.is_banned:
                print(f"🚫 Banned user {real_username} attempted heartbeat pulse. Exorcising.")
                await sio.disconnect(sid)
                return
                
            # Safely award experience/authenticity points over live waves
            user.auth_points += 1
            db.add(user)
            db.commit()
        else:
            print(f"⚠️ Heartbeat skipped: No db anchor found for user '{real_username}'")

