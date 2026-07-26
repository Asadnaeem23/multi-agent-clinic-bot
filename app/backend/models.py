from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ChatMessageInput(BaseModel):
    message: str
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    thread_id: Optional[str] = None

class ChatMessageResponse(BaseModel):
    role: str
    content: str
    agent: Optional[str] = None
    thread_id: str
    chat_status: str

class BookingCreate(BaseModel):
    user_id: int
    service: str
    doctor: str
    appointment_date: datetime
    notes: Optional[str] = None

class BookingUpdate(BaseModel):
    service: Optional[str] = None
    doctor: Optional[str] = None
    appointment_date: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class BookingResponse(BaseModel):
    id: int
    user_id: int
    service: str
    doctor: str
    appointment_date: datetime
    status: str
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    id: int
    user_id: int
    thread_id: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    id: int
    chat_id: int
    role: str
    content: str
    agent: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class BusinessSettingsUpdate(BaseModel):
    clinic_name: Optional[str] = None
    business_hours: Optional[str] = None
    services: Optional[str] = None
    doctors: Optional[str] = None
    pricing: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    policies: Optional[str] = None

class BlockoutCreate(BaseModel):
    doctor: Optional[str] = None  # doctor name or "All"
    start_time: datetime
    end_time: datetime
    reason: Optional[str] = None

class BlockoutResponse(BaseModel):
    id: int
    doctor: Optional[str] = None
    start_time: datetime
    end_time: datetime
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
class SettingsConfigUpdate(BaseModel):
    groq_api_key: Optional[str] = None
    model_supervisor: Optional[str] = None
    model_inquiry: Optional[str] = None
    model_booking: Optional[str] = None
    model_human_handoff: Optional[str] = None
    api_key_supervisor: Optional[str] = None
    api_key_inquiry: Optional[str] = None
    api_key_booking: Optional[str] = None
    api_key_human_handoff: Optional[str] = None

