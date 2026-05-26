from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db.session import get_session
from app.db.models import User, UserRead
from app.api.deps import get_current_user
from app.redis_cache.connection import redis_client

router = APIRouter()

from sqlmodel import SQLModel

class BioUpdate(SQLModel):
    bio: str

@router.get("/me", response_model=UserRead)
def get_my_dashboard(current_user: User = Depends(get_current_user)):
    """The frontend calls this to load the Dashboard stats."""
    return current_user

@router.put("/me", response_model=UserRead)
def update_bio(
    bio_in: BioUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Updates the logged in user's permanent bio."""
    current_user.bio = bio_in.bio
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/ghost/{ghost_name}")
def get_ghost_profile(ghost_name: str, db: Session = Depends(get_session)):
    """When a user clicks on a ghost in the chatroom to see their bio."""
    # 1. Look up the pointer in Redis
    real_username = redis_client.get(f"ghost_pointer:{ghost_name}")
    if not real_username:
        raise HTTPException(status_code=404, detail="Ghost vanished or does not exist.")
        
    # 2. Fetch their public info from Postgres
    user = db.exec(select(User).where(User.username == real_username)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Identity anchor has faded from persistent memory.")
        
    # 3. Get their active Socket SID
    target_sid = redis_client.get(f"ghost_to_sid:{ghost_name}")
    
    # 4. ONLY return the safe data (No permanent username!)
    return {
        "ghost_name": ghost_name,
        "bio": user.bio,
        "auth_points": user.auth_points,
        "sid": target_sid
    }

@router.post("/gift/{ghost_name}")
def gift_authenticity_point(
    ghost_name: str, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_session)
):
    """Transfer an authenticity point to a ghost."""
    # 1. Look up who the ghost really is
    target_username = redis_client.get(f"ghost_pointer:{ghost_name}")
    
    if not target_username:
        raise HTTPException(status_code=404, detail="Ghost not found.")
    
    if target_username == current_user.username:
        raise HTTPException(status_code=400, detail="You cannot gift points to yourself!")

    # 2. Find the target user in Postgres
    target_user = db.exec(select(User).where(User.username == target_username)).first()
    
    # 3. Add the point and save to the permanent database
    target_user.auth_points += 1
    db.add(target_user)
    db.commit()
    
    return {"message": f"Successfully gifted a point to {ghost_name}!"}

@router.post("/report/{ghost_name}")
async def report_user(
    ghost_name: str,
    room_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Report a ghost for fake/bot activity.
    Each report deducts 5 Authenticity Points.
    At 3 flags, the user is banned (is_banned=True), loses 10 additional points, and gets kicked out of the chat.
    """
    from app.sockets.server import sio
    
    # 1. Resolve ghost name
    target_username = redis_client.get(f"ghost_pointer:{ghost_name}")
    if not target_username:
        raise HTTPException(status_code=404, detail="Ghost not found or has faded away.")
        
    if target_username == current_user.username:
        raise HTTPException(status_code=400, detail="You cannot report your own manifestation.")
        
    # 2. Anti-spam: check if this user already reported the target
    report_key = f"user:reports:{target_username}"
    if redis_client.sismember(report_key, current_user.username):
        raise HTTPException(status_code=400, detail="You have already reported this identity.")
        
    # Record report
    redis_client.sadd(report_key, current_user.username)
    redis_client.expire(report_key, 86400) # Expiry of 24h
    
    num_reports = redis_client.scard(report_key)
    
    # 3. Fetch target user in Postgres
    target_user = db.exec(select(User).where(User.username == target_username)).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Underlying account not found.")
        
    # 4. Apply penalty
    target_user.auth_points -= 5
    
    is_ban_triggered = False
    if num_reports >= 3:
        target_user.is_banned = True
        target_user.auth_points -= 10 # Account Slash Penalty (total -15)
        is_ban_triggered = True
        
    db.add(target_user)
    db.commit()
    
    # 5. Broadcast to room and handle socket kick if banned
    target_sid = redis_client.get(f"ghost_to_sid:{ghost_name}")
    
    if is_ban_triggered:
        # Broadcast ban
        await sio.emit("system_message", {
            "msg": f"⚡ Ghost {ghost_name} has been EXORCISED from the void (3/3 Reports)."
        }, room=room_name)
        # Disconnect target's socket
        if target_sid:
            await sio.disconnect(target_sid)
    else:
        # Broadcast warning
        await sio.emit("system_message", {
            "msg": f"⚠️ Ghost {ghost_name} was reported by another ghost ({num_reports}/3 flags)."
        }, room=room_name)
        
    return {
        "message": f"Successfully reported {ghost_name}.",
        "reports": num_reports,
        "banned": is_ban_triggered
    }
