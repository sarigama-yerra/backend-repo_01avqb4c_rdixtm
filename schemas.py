"""
Database Schemas for Psylio-style app

Each Pydantic model name maps to a MongoDB collection with the lowercase
class name (e.g., User -> "user").
"""

from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional


class User(BaseModel):
    """User collection: both clients and therapists"""
    role: str = Field(..., description="client or therapist")
    name: str
    email: EmailStr
    photo_url: Optional[str] = None
    bio: Optional[str] = None
    specialties: List[str] = Field(default_factory=list)
    modalities: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    virtual: bool = True
    in_person: bool = False
    fee_min: Optional[int] = None
    fee_max: Optional[int] = None
    years_experience: Optional[int] = None
    certifications: List[str] = Field(default_factory=list)


class TherapistAvailability(BaseModel):
    therapist_id: str
    weekday: int = Field(..., ge=0, le=6, description="0=Mon .. 6=Sun")
    time_ranges: List[str] = Field(..., description="e.g., ['09:00-12:00','14:00-17:00']")
    virtual: bool = True
    in_person: bool = False


class BookingRequest(BaseModel):
    therapist_id: str
    client_name: str
    client_email: EmailStr
    note: Optional[str] = None
    preferred_times: List[str] = Field(default_factory=list)
    status: str = Field(default="pending", description="pending|accepted|declined|completed")


class Message(BaseModel):
    therapist_id: str
    client_email: EmailStr
    from_email: EmailStr
    to_email: EmailStr
    content: str
    thread_id: Optional[str] = None


class JournalEntry(BaseModel):
    client_email: EmailStr
    title: str
    content: str
    mood: Optional[str] = None
