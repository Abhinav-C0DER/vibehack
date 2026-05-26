from fastapi import APIRouter, Depends
from app.redis_cache.manager import RoomManager
from app.api.deps import get_current_user
from app.db.models import User

router = APIRouter()

@router.get("/trending")
def get_trending_rooms():
    """
    Returns the top active chatrooms. 
    If all rooms are empty, it returns an empty list.
    """
    rooms = RoomManager.get_trending_rooms()
    return {"trending_rooms": rooms}

@router.get("/recommended")
def get_recommended_rooms(current_user: User = Depends(get_current_user)):
    """
    Scans the user's bio for key tech and lifestyle interest tags,
    compares them to active room names/categories, and returns highly relevant suggestions.
    """
    # 1. Fetch active rooms
    rooms = RoomManager.get_trending_rooms(limit=20)
    
    bio = (current_user.bio or "").lower()
    
    # Pre-defined interest keywords
    KEYWORDS = {
        "python", "rust", "javascript", "typescript", "c++", "c#", "java", "go",
        "coding", "development", "dev", "gaming", "music", "anime", "chill", 
        "ai", "llm", "space", "hacking", "crypto", "security", "art", "movies"
    }
    
    # 2. Extract matched keywords from bio
    matched_interests = [kw for kw in KEYWORDS if kw in bio]
    
    recommended_rooms = []
    other_rooms = []
    
    for r in rooms:
        name = r["room_name"].lower()
        category = (r["category"] or "").lower()
        
        # Check if name or category matches any bio interest
        match_count = sum(1 for kw in matched_interests if kw in name or kw in category)
        
        if match_count > 0 or (not matched_interests and r["user_count"] > 0):
            r["is_recommended"] = True
            r["match_score"] = match_count
            recommended_rooms.append(r)
        else:
            r["is_recommended"] = False
            r["match_score"] = 0
            other_rooms.append(r)
            
    # Sort recommendations by match count and user count
    recommended_rooms.sort(key=lambda x: (x["match_score"], x["user_count"]), reverse=True)
    
    return {
        "recommended_rooms": recommended_rooms,
        "other_rooms": other_rooms,
        "matched_keywords": matched_interests
    }
