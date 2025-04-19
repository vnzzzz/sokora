"""
Location schemas
==============

Pydantic schemas for location data validation and serialization.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class LocationBase(BaseModel):
    """Base schema for location data"""

    name: str
    color_code: Optional[str] = None


class LocationCreate(LocationBase):
    """Schema for creating a new location type"""

    pass


class LocationUpdate(LocationBase):
    """Schema for updating location data"""

    name: Optional[str] = None


class LocationInDBBase(LocationBase):
    """Base schema for location with DB ID"""

    id: int

    class Config:
        orm_mode = True


class Location(LocationInDBBase):
    """Schema for location data response"""

    pass


class LocationList(BaseModel):
    """Schema for list of locations"""

    locations: List[Location]
