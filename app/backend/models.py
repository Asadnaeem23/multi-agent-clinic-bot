from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import List, Literal, Optional
from datetime import datetime

class ChatMessageInput(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    thread_id: Optional[str] = None

    @field_validator("message")
    @classmethod
    def strip_chat_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message cannot be blank")
        return value

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
    status: Optional[Literal["scheduled", "completed", "cancelled"]] = None
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

class BusinessContextUpdate(BaseModel):
    business_context: str = Field(min_length=1, max_length=100000)

    @field_validator("business_context")
    @classmethod
    def strip_context(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("business context cannot be blank")
        return value

class AdminReplyInput(BaseModel):
    content: str = Field(min_length=1, max_length=8000)

    @field_validator("content")
    @classmethod
    def strip_reply(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reply cannot be blank")
        return value

class GuardrailTestInput(BaseModel):
    message: str = Field(min_length=1, max_length=8000)

    @field_validator("message")
    @classmethod
    def strip_test_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message cannot be blank")
        return value

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
    model_config = ConfigDict(extra="forbid")

    groq_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    openrouter_site_url: Optional[str] = None
    openrouter_app_name: Optional[str] = None
    provider_supervisor: Optional[Literal["groq", "openrouter"]] = None
    provider_inquiry: Optional[Literal["groq", "openrouter"]] = None
    provider_booking: Optional[Literal["groq", "openrouter"]] = None
    provider_human_handoff: Optional[Literal["groq", "openrouter"]] = None
    provider_guardrail: Optional[Literal["groq", "openrouter"]] = None
    model_supervisor: Optional[str] = None
    model_inquiry: Optional[str] = None
    model_booking: Optional[str] = None
    model_human_handoff: Optional[str] = None
    model_guardrail: Optional[str] = None
    api_key_supervisor: Optional[str] = None
    api_key_inquiry: Optional[str] = None
    api_key_booking: Optional[str] = None
    api_key_human_handoff: Optional[str] = None
    api_key_guardrail: Optional[str] = None
    guardrails_enabled: Optional[bool] = None
    guardrail_heuristics_enabled: Optional[bool] = None
    guardrail_system_prompt: Optional[str] = None
    guardrail_injection_response: Optional[str] = None
    guardrail_irrelevant_response: Optional[str] = None
    guardrail_failure_response: Optional[str] = None
    guardrail_failure_mode: Optional[Literal["block", "allow"]] = None

    @field_validator(
        "model_supervisor", "model_inquiry", "model_booking",
        "model_human_handoff", "model_guardrail",
        "guardrail_system_prompt", "guardrail_injection_response",
        "guardrail_irrelevant_response", "guardrail_failure_response",
    )
    @classmethod
    def reject_blank_required_text(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("value cannot be blank")
        return value.strip() if value is not None else value
