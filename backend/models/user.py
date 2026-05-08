"""
User models
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid


class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    coins: int = 0
    daily_login_streak: int = 0
    last_login_date: Optional[str] = None
    profile_completed: bool = False
    bio: str = ""
    avatar_url: str = ""
    total_spent_coins: int = 0
    monthly_logins: dict = Field(default_factory=dict)
    unlocked_series: List[int] = Field(default_factory=lambda: [1])
    completed_series: List[int] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserCard(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    card_id: str
    quantity: int = 1
    acquired_at: datetime = Field(default_factory=datetime.utcnow)


class CreateUserRequest(BaseModel):
    username: str


class UpdateProfileRequest(BaseModel):
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
