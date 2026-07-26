from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime, timezone
from langchain_core.messages import HumanMessage, AIMessage

# Import local modules
from database import init_db, get_db, User, Chat, Message, Booking, BusinessSettings, Blockout
from models import (
    ChatMessageInput, ChatMessageResponse, BookingCreate, BookingUpdate, 
    BookingResponse, UserCreate, UserResponse, ChatResponse, MessageResponse,
    BusinessSettingsUpdate, BlockoutCreate, BlockoutResponse, SettingsConfigUpdate
)
from graph import build_graph
from config import get_business_context, update_business_context, DEFAULT_BUSINESS_CONTEXT

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Initialize database
init_db()

# Build LangGraph
graph = build_graph()

# Create the main app
app = FastAPI(title="AI Customer Support API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ==================== Chat Endpoints ====================

@api_router.post("/chat", response_model=ChatMessageResponse)
async def chat(input: ChatMessageInput, db: Session = Depends(get_db)):
    """Handle chat messages and route through LangGraph agents"""
    
    # Get or create user
    if input.user_id:
        user = db.query(User).filter(User.id == input.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    elif input.user_email:
        user = db.query(User).filter(User.email == input.user_email).first()
        if not user:
            user = User(
                name=input.user_name or "Guest",
                email=input.user_email,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    else:
        # Create anonymous user
        user = User(
            name=input.user_name or f"Guest_{uuid.uuid4().hex[:8]}",
            email=f"guest_{uuid.uuid4().hex[:8]}@temp.com",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Get or create chat
    if input.thread_id:
        chat = db.query(Chat).filter(Chat.thread_id == input.thread_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
    else:
        thread_id = str(uuid.uuid4())
        chat = Chat(
            user_id=user.id,
            thread_id=thread_id,
            status="active"
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)
    
    # Save user message
    user_message = Message(
        chat_id=chat.id,
        role="user",
        content=input.message
    )
    db.add(user_message)
    db.commit()
    
    # Get conversation history
    messages = db.query(Message).filter(Message.chat_id == chat.id).order_by(Message.created_at).all()
    
    # Convert to LangChain messages
    lc_messages = []
    for msg in messages:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_messages.append(AIMessage(content=msg.content))
    
    # Get business context
    business_context = get_business_context(db)
    
    # Prepare state for LangGraph
    state = {
        "messages": lc_messages,
        "thread_id": chat.thread_id,
        "active_agent": "",
        "user_intent": "",
        "business_context": business_context
    }
    
    # Run through LangGraph
    result = graph.invoke(state)
    
    # Extract AI response
    ai_response = result["messages"][-1].content
    active_agent = result["active_agent"]
    user_intent = result.get("user_intent", "")
    
    # Save AI message
    ai_message = Message(
        chat_id=chat.id,
        role="assistant",
        content=ai_response,
        agent=active_agent
    )
    db.add(ai_message)
    
    # Update chat status if human handoff
    if user_intent == "human_handoff":
        chat.status = "waiting_human"
    
    chat.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ai_message)
    
    return ChatMessageResponse(
        role="assistant",
        content=ai_response,
        agent=active_agent,
        thread_id=chat.thread_id,
        chat_status=chat.status
    )

@api_router.get("/chats", response_model=List[ChatResponse])
async def get_chats(status: str = None, db: Session = Depends(get_db)):
    """Get all chats, optionally filtered by status"""
    query = db.query(Chat)
    if status:
        query = query.filter(Chat.status == status)
    chats = query.order_by(Chat.updated_at.desc()).all()
    return chats

@api_router.get("/chats/{thread_id}/messages", response_model=List[MessageResponse])
async def get_chat_messages(thread_id: str, db: Session = Depends(get_db)):
    """Get all messages for a specific chat"""
    chat = db.query(Chat).filter(Chat.thread_id == thread_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    messages = db.query(Message).filter(Message.chat_id == chat.id).order_by(Message.created_at).all()
    return messages

@api_router.put("/chats/{thread_id}/status")
async def update_chat_status(thread_id: str, status: str, db: Session = Depends(get_db)):
    """Update chat status (for admin to take over or close)"""
    chat = db.query(Chat).filter(Chat.thread_id == thread_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    chat.status = status
    chat.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    return {"message": "Chat status updated", "thread_id": thread_id, "status": status}

@api_router.delete("/chats/{thread_id}")
async def delete_chat(thread_id: str, db: Session = Depends(get_db)):
    """Delete a chat session and all its messages."""
    chat = db.query(Chat).filter(Chat.thread_id == thread_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Delete all associated messages first to maintain referential integrity
    db.query(Message).filter(Message.chat_id == chat.id).delete()
    
    # Delete the chat
    db.delete(chat)
    db.commit()
    
    return {"message": "Chat and its messages successfully deleted"}

@api_router.post("/chats/{thread_id}/admin-reply")
async def admin_reply(thread_id: str, content: str, db: Session = Depends(get_db)):
    """Admin manually replies to a chat"""
    chat = db.query(Chat).filter(Chat.thread_id == thread_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    admin_message = Message(
        chat_id=chat.id,
        role="assistant",
        content=content,
        agent="admin"
    )
    db.add(admin_message)
    chat.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    return {"message": "Reply sent", "thread_id": thread_id}

# ==================== Booking Endpoints ====================

@api_router.post("/bookings", response_model=BookingResponse)
async def create_booking(booking: BookingCreate, db: Session = Depends(get_db)):
    """Create a new booking"""
    user = db.query(User).filter(User.id == booking.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_booking = Booking(
        user_id=booking.user_id,
        service=booking.service,
        doctor=booking.doctor,
        appointment_date=booking.appointment_date,
        notes=booking.notes
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    
    return new_booking

@api_router.get("/bookings", response_model=List[BookingResponse])
async def get_bookings(status: str = None, db: Session = Depends(get_db)):
    """Get all bookings, optionally filtered by status"""
    query = db.query(Booking)
    if status:
        query = query.filter(Booking.status == status)
    bookings = query.order_by(Booking.appointment_date.desc()).all()
    return bookings

@api_router.get("/bookings/{booking_id}", response_model=BookingResponse)
async def get_booking(booking_id: int, db: Session = Depends(get_db)):
    """Get a specific booking"""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

@api_router.put("/bookings/{booking_id}", response_model=BookingResponse)
async def update_booking(booking_id: int, booking_update: BookingUpdate, db: Session = Depends(get_db)):
    """Update a booking"""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    update_data = booking_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(booking, key, value)
    
    db.commit()
    db.refresh(booking)
    return booking

@api_router.delete("/bookings/{booking_id}")
async def delete_booking(booking_id: int, db: Session = Depends(get_db)):
    """Delete a booking"""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    db.delete(booking)
    db.commit()
    return {"message": "Booking deleted", "booking_id": booking_id}

# ==================== User Endpoints ====================

@api_router.post("/users", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        name=user.name,
        email=user.email,
        phone=user.phone
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@api_router.get("/users", response_model=List[UserResponse])
async def get_users(db: Session = Depends(get_db)):
    """Get all users"""
    users = db.query(User).all()
    return users

# ==================== Business Settings Endpoints ====================

@api_router.get("/settings/context")
async def get_context(db: Session = Depends(get_db)):
    """Get current business context"""
    context = get_business_context(db)
    return {"business_context": context}

@api_router.put("/settings/context")
async def update_context(new_context: str, db: Session = Depends(get_db)):
    """Update business context"""
    update_business_context(db, new_context)
    return {"message": "Business context updated"}

@api_router.post("/settings/reset")
async def reset_context(db: Session = Depends(get_db)):
    """Reset business context to default"""
    update_business_context(db, DEFAULT_BUSINESS_CONTEXT)
    return {"message": "Business context reset to default"}

@api_router.get("/settings/config")
async def get_config(db: Session = Depends(get_db)):
    """Get LLM models and API Key settings from database or fallback to env variables"""
    keys = [
        "groq_api_key", "model_supervisor", "model_inquiry", "model_booking", "model_human_handoff",
        "api_key_supervisor", "api_key_inquiry", "api_key_booking", "api_key_human_handoff"
    ]
    config_dict = {}
    for key in keys:
        setting = db.query(BusinessSettings).filter(BusinessSettings.key == key).first()
        if setting:
            config_dict[key] = setting.value
        else:
            if key == "groq_api_key":
                config_dict[key] = os.getenv("GROQ_API_KEY", "")
            elif key == "model_supervisor":
                config_dict[key] = "llama-3.1-8b-instant"
            elif key == "model_inquiry":
                config_dict[key] = "llama-3.3-70b-versatile"
            elif key == "model_booking":
                config_dict[key] = "llama-3.3-70b-versatile"
            elif key == "model_human_handoff":
                config_dict[key] = "llama-3.1-8b-instant"
            else:
                # Default for agent specific api keys is empty (falls back to global groq_api_key)
                config_dict[key] = ""
    return config_dict

@api_router.put("/settings/config")
async def update_config(config: SettingsConfigUpdate, db: Session = Depends(get_db)):
    """Update LLM models and API Key settings in database"""
    config_data = config.model_dump(exclude_unset=True)
    for key, value in config_data.items():
        if value is not None:
            setting = db.query(BusinessSettings).filter(BusinessSettings.key == key).first()
            if setting:
                setting.value = value.strip()
            else:
                setting = BusinessSettings(key=key, value=value.strip())
                db.add(setting)
    db.commit()
    return {"message": "Configuration settings updated successfully"}


# ==================== Blockout Endpoints ====================

@api_router.post("/blockouts", response_model=BlockoutResponse)
async def create_blockout(blockout: BlockoutCreate, db: Session = Depends(get_db)):
    """Create a new blockout slot"""
    db_blockout = Blockout(
        doctor=blockout.doctor,
        start_time=blockout.start_time,
        end_time=blockout.end_time,
        reason=blockout.reason
    )
    db.add(db_blockout)
    db.commit()
    db.refresh(db_blockout)
    return db_blockout

@api_router.get("/blockouts", response_model=List[BlockoutResponse])
async def get_blockouts(db: Session = Depends(get_db)):
    """Get all blockout slots"""
    return db.query(Blockout).order_by(Blockout.start_time.asc()).all()

@api_router.delete("/blockouts/{blockout_id}")
async def delete_blockout(blockout_id: int, db: Session = Depends(get_db)):
    """Delete a blockout slot"""
    db_blockout = db.query(Blockout).filter(Blockout.id == blockout_id).first()
    if not db_blockout:
        raise HTTPException(status_code=404, detail="Blockout slot not found")
    db.delete(db_blockout)
    db.commit()
    return {"message": "Blockout slot deleted", "blockout_id": blockout_id}

# ==================== Dashboard Stats ====================

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    total_chats = db.query(Chat).count()
    active_chats = db.query(Chat).filter(Chat.status == "active").count()
    waiting_human = db.query(Chat).filter(Chat.status == "waiting_human").count()
    
    today = datetime.now(timezone.utc).date()
    todays_bookings = db.query(Booking).filter(
        Booking.appointment_date >= datetime.combine(today, datetime.min.time()),
        Booking.appointment_date < datetime.combine(today, datetime.max.time())
    ).count()
    
    total_bookings = db.query(Booking).count()
    scheduled_bookings = db.query(Booking).filter(Booking.status == "scheduled").count()
    
    return {
        "total_chats": total_chats,
        "active_chats": active_chats,
        "waiting_human": waiting_human,
        "todays_bookings": todays_bookings,
        "total_bookings": total_bookings,
        "scheduled_bookings": scheduled_bookings
    }

# ==================== Root Endpoint ====================

@api_router.get("/")
async def root():
    return {"message": "AI Customer Support API", "status": "running"}

# Include the router in the main app
app.include_router(api_router)

# Serve frontend static files
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
