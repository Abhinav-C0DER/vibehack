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

