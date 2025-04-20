"""
User schemas
===========

Pydantic schemas for user data validation and serialization.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """Base schema for user data"""

    username: str
    user_id: str


class UserCreate(UserBase):
    """Schema for creating a new user"""

    pass


class UserUpdate(UserBase):
    """Schema for updating user data"""

    username: Optional[str] = None
    user_id: Optional[str] = None


class UserInDBBase(UserBase):
    """Base schema for user with DB ID"""

    id: int

    class Config:
        orm_mode = True


class User(UserInDBBase):
    """Schema for user data response"""

    pass


class UserList(BaseModel):
    """Schema for list of users"""

    users: List[User]
