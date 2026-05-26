from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
import uuid

class User(SQLModel, table=True):
    # Internal unique ID
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    
    # Public-facing Permanent Username (What they use to login)
    username: str = Field(unique=True, index=True)
    
    # Hashed Password (Never store plain text!)
    hashed_password: str
    
    # User's interests/bio
    bio: Optional[str] = Field(default="A mysterious ghost...")
    
    # Reputation system
    auth_points: int = Field(default=0)
    
    # Account status
    is_banned: bool = Field(default=False)
    
    # Account age
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(SQLModel):
    """Schema for Registration"""
    username: str
    password: str

class UserRead(SQLModel):
    """Schema for Dashboard (No password!)"""
    username: str
    bio: Optional[str]
    auth_points: int
