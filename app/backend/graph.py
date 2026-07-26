from typing import Annotated, TypedDict
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
import os
from datetime import datetime
from database import SessionLocal, Chat, User, Booking, Blockout, BusinessSettings
from langchain_core.tools import tool

class ChatState(TypedDict):
    messages: Annotated[list, "Conversation messages"]
    thread_id: str
    active_agent: str
    user_intent: str
    business_context: str

def get_setting(key: str, default_val: str) -> str:
    db = SessionLocal()
    try:
        setting = db.query(BusinessSettings).filter(BusinessSettings.key == key).first()
        if setting and setting.value.strip():
            return setting.value.strip()
        # Fallback to env
        env_val = os.getenv(key.upper())
        if env_val:
            return env_val
        return default_val
    finally:
        db.close()

def create_llm(agent_name: str):
    # Try agent-specific API key first, then fall back to global groq_api_key, then environment variable
    api_key = get_setting(f"api_key_{agent_name}", "")
    if not api_key:
        api_key = get_setting("groq_api_key", os.getenv("GROQ_API_KEY", ""))
    
    default_models = {
        "supervisor": "llama-3.1-8b-instant",
        "inquiry": "llama-3.3-70b-versatile",
        "booking": "llama-3.3-70b-versatile",
        "human_handoff": "llama-3.1-8b-instant"
    }
    
    default_temps = {
        "supervisor": 0.0,
        "inquiry": 0.3,
        "booking": 0.1,
        "human_handoff": 0.0
    }
    
    model = get_setting(f"model_{agent_name}", default_models[agent_name])
    temp = default_temps[agent_name]
    
    return ChatGroq(
        model=model,
        temperature=temp,
        groq_api_key=api_key,
    )

def supervisor_node(state: ChatState) -> ChatState:
    """Supervisor agent that routes to appropriate agent based on user intent"""
    llm = create_llm("supervisor")
    
    system_prompt = """You are a routing supervisor for a customer support AI system.
    Analyze the user's message and determine their intent.
    
    Intents:
    - 'inquiry': Questions about services, hours, doctors, pricing, policies
    - 'booking': Create, cancel, reschedule, or check appointment bookings
    - 'human_handoff': User explicitly requests to talk to a human
    
    Respond with ONLY ONE WORD: inquiry, booking, or human_handoff"""
    
    last_user_msg = state["messages"][-1]
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User message: {last_user_msg.content}")
    ]
    
    response = llm.invoke(messages)
    intent = response.content.strip().lower()
    
    # Validate intent
    if intent not in ["inquiry", "booking", "human_handoff"]:
        intent = "inquiry"  # Default to inquiry
    
    state["user_intent"] = intent
    state["active_agent"] = "supervisor"
    
    return state

def inquiry_node(state: ChatState) -> ChatState:
    """Inquiry agent that answers questions about the business"""
    llm = create_llm("inquiry")
    
    system_prompt = f"""You are a helpful customer support assistant for a dental clinic.
    
    Use the following business information to answer customer questions:
    
    {state['business_context']}
    
    Provide accurate, friendly, and professional responses. If you don't have specific information, 
    be honest and suggest they contact the clinic or speak with a staff member."""
    
    # Get conversation history
    messages = [SystemMessage(content=system_prompt)]
    
    # Add conversation history (exclude system messages)
    for msg in state["messages"]:
        if msg.type != "system":
            messages.append(msg)
    
    response = llm.invoke(messages)
    
    # Add response to state
    ai_message = AIMessage(content=response.content)
    state["messages"].append(ai_message)
    state["active_agent"] = "inquiry"
    
    return state

def parse_date(date_str: str) -> datetime:
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"Could not parse date: {date_str}")

@tool
def book_appointment(thread_id: str, service: str, doctor: str, appointment_date: str, notes: str = None) -> str:
    """Book a new appointment for the customer.
    thread_id: unique chat session ID (automatically provided from context).
    service: service name (e.g. Routine Check-up, Teeth Cleaning, Fillings, Root Canal, Teeth Whitening, Veneers, Metal Braces, Ceramic Braces, Clear Aligners, Emergency Care).
    doctor: doctor name (e.g. Dr. Ahmed Khan, Dr. Ayesha Malik, Dr. Hassan Ali).
    appointment_date: requested date and time in YYYY-MM-DD HH:MM:SS format.
    notes: optional additional notes.
    """
    db = SessionLocal()
    try:
        chat = db.query(Chat).filter(Chat.thread_id == thread_id).first()
        if not chat or not chat.user:
            return "Error: User or Chat session not found. Please start the chat again."
        
        try:
            parsed_date = parse_date(appointment_date)
        except Exception as e:
            return f"Error: Invalid date format. Please specify date in YYYY-MM-DD HH:MM:SS format."
            
        # Check if requested time is blocked
        blockout = db.query(Blockout).filter(
            Blockout.start_time <= parsed_date,
            Blockout.end_time >= parsed_date
        ).filter(
            (Blockout.doctor == "All") | (Blockout.doctor == doctor)
        ).first()
        
        if blockout:
            reason_str = f" due to {blockout.reason}" if blockout.reason else ""
            return f"Error: The requested slot on {parsed_date.strftime('%Y-%m-%d %I:%M %p')} is unavailable{reason_str}. Please select another date or time."
            
        booking = Booking(
            user_id=chat.user.id,
            service=service,
            doctor=doctor,
            appointment_date=parsed_date,
            status="scheduled",
            notes=notes
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        return f"SUCCESS: Booking successfully created! Booking Reference ID: #{booking.id}. Service: {service}, Doctor: {doctor}, Date/Time: {booking.appointment_date.strftime('%Y-%m-%d %I:%M %p')}."
    except Exception as e:
        db.rollback()
        return f"Error creating booking: {str(e)}"
    finally:
        db.close()

@tool
def cancel_appointment(booking_id: int) -> str:
    """Cancel an existing appointment.
    booking_id: the reference ID of the booking (e.g. 1, 2, 3, etc.).
    """
    # Force booking_id conversion to int in case LLM passes string
    try:
        booking_id = int(booking_id)
    except ValueError:
        return "Error: booking_id must be a numeric integer."
        
    db = SessionLocal()
    try:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            return f"Error: No booking found with Booking Reference ID #{booking_id}."
        
        booking.status = "cancelled"
        db.commit()
        return f"SUCCESS: Booking Reference ID #{booking_id} has been successfully cancelled."
    except Exception as e:
        db.rollback()
        return f"Error cancelling booking: {str(e)}"
    finally:
        db.close()

@tool
def reschedule_appointment(booking_id: int, new_date: str) -> str:
    """Reschedule an existing appointment.
    booking_id: the reference ID of the booking (e.g. 1, 2, 3, etc.).
    new_date: the new date and time requested in YYYY-MM-DD HH:MM:SS format.
    """
    try:
        booking_id = int(booking_id)
    except ValueError:
        return "Error: booking_id must be a numeric integer."
        
    db = SessionLocal()
    try:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            return f"Error: No booking found with Booking Reference ID #{booking_id}."
        
        try:
            parsed_date = parse_date(new_date)
        except Exception as e:
            return f"Error: Invalid date format. Please specify date in YYYY-MM-DD HH:MM:SS format."
            
        # Check if rescheduled time is blocked
        blockout = db.query(Blockout).filter(
            Blockout.start_time <= parsed_date,
            Blockout.end_time >= parsed_date
        ).filter(
            (Blockout.doctor == "All") | (Blockout.doctor == booking.doctor)
        ).first()
        
        if blockout:
            reason_str = f" due to {blockout.reason}" if blockout.reason else ""
            return f"Error: The rescheduled slot on {parsed_date.strftime('%Y-%m-%d %I:%M %p')} is unavailable{reason_str}. Please select another date or time."
            
        booking.appointment_date = parsed_date
        booking.status = "scheduled"
        db.commit()
        return f"SUCCESS: Booking Reference ID #{booking_id} has been successfully rescheduled to {booking.appointment_date.strftime('%Y-%m-%d %I:%M %p')}."
    except Exception as e:
        db.rollback()
        return f"Error rescheduling booking: {str(e)}"
    finally:
        db.close()

@tool
def get_user_bookings(thread_id: str) -> str:
    """Check/List all existing appointments for the current customer.
    thread_id: unique chat session ID (automatically provided from context).
    """
    db = SessionLocal()
    try:
        chat = db.query(Chat).filter(Chat.thread_id == thread_id).first()
        if not chat or not chat.user:
            return "Error: User or Chat session not found."
        
        bookings = db.query(Booking).filter(Booking.user_id == chat.user.id).all()
        if not bookings:
            return f"You currently have no appointments booked under the name: {chat.user.name}."
        
        lines = [f"Appointments for {chat.user.name}:"]
        for b in bookings:
            lines.append(f"- Booking Reference ID: #{b.id} | Service: {b.service} | Doctor: {b.doctor} | Date: {b.appointment_date.strftime('%Y-%m-%d %I:%M %p')} | Status: {b.status}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching appointments: {str(e)}"
    finally:
        db.close()

def booking_node(state: ChatState) -> ChatState:
    """Booking agent that handles appointment-related requests"""
    tools = [book_appointment, cancel_appointment, reschedule_appointment, get_user_bookings]
    tool_map = {t.name: t for t in tools}
    
    llm = create_llm("booking").bind_tools(tools)
    
    current_time = datetime.now().strftime("%A, %B %d, %Y %I:%M %p")
    
    system_prompt = f"""You are a booking assistant for a dental clinic.
    
    Business Information:
    {state['business_context']}
    
    Current Date & Time: {current_time}
    
    Your job is to assist customers with their appointments:
    - Checking their existing bookings
    - Creating new bookings (requires collecting: service name, doctor name, and preferred date/time)
    - Cancelling bookings (requires booking reference ID or identifying their active booking)
    - Rescheduling bookings (requires booking reference ID and new preferred date/time)
    
    Guidelines:
    1. For any action (booking, rescheduling, cancelling, listing), use the appropriate tool.
    2. Crucial: ALWAYS pass the exact thread_id as the 'thread_id' parameter when calling `book_appointment` or `get_user_bookings`. The current thread_id is: '{state["thread_id"]}'. Do NOT ask the user for the thread_id.
    3. Be conversational and friendly. If you are missing details needed to book (like service, doctor, or date), ask the user naturally.
    4. Confirm details before scheduling a new booking.
    5. Always state the booking reference ID (e.g. #1) to the customer when confirming booking placement, rescheduling, or cancellation.
    """
    
    messages = [SystemMessage(content=system_prompt)]
    
    for msg in state["messages"]:
        if msg.type != "system":
            messages.append(msg)
            
    response = llm.invoke(messages)
    
    # Tool execution loop
    while response.tool_calls:
        messages.append(response)
        
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_id = tool_call["id"]
            
            if tool_name in tool_map:
                tool_func = tool_map[tool_name]
                try:
                    tool_output = tool_func.invoke(tool_args)
                except Exception as e:
                    tool_output = f"Error executing tool: {str(e)}"
            else:
                tool_output = f"Error: Tool {tool_name} not found."
                
            tool_message = ToolMessage(content=str(tool_output), tool_call_id=tool_id)
            messages.append(tool_message)
            
        response = llm.invoke(messages)
        
    state["messages"].append(response)
    state["active_agent"] = "booking"
    
    return state

def human_handoff_node(state: ChatState) -> ChatState:
    """Human handoff agent that handles requests for human assistance"""
    llm = create_llm("human_handoff")
    
    system_prompt = """You are a human handoff assistant. The customer has requested to speak with a human.
    
    Provide a friendly message that:
    1. Acknowledges their request
    2. Informs them a staff member will be with them shortly
    3. Thanks them for their patience
    
    Keep it brief and professional."""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="The user wants to speak with a human.")
    ]
    
    response = llm.invoke(messages)
    
    ai_message = AIMessage(content=response.content)
    state["messages"].append(ai_message)
    state["active_agent"] = "human_handoff"
    
    return state

def route_after_supervisor(state: ChatState) -> str:
    """Route to the appropriate agent based on supervisor's intent detection"""
    intent = state.get("user_intent", "inquiry")
    
    if intent == "booking":
        return "booking"
    elif intent == "human_handoff":
        return "human_handoff"
    else:
        return "inquiry"

def build_graph():
    """Build the LangGraph workflow"""
    builder = StateGraph(ChatState)
    
    # Add nodes
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("inquiry", inquiry_node)
    builder.add_node("booking", booking_node)
    builder.add_node("human_handoff", human_handoff_node)
    
    # Set entry point
    builder.add_edge(START, "supervisor")
    
    # Add conditional edges from supervisor
    builder.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "inquiry": "inquiry",
            "booking": "booking",
            "human_handoff": "human_handoff",
        },
    )
    
    # All agents lead to END
    builder.add_edge("inquiry", END)
    builder.add_edge("booking", END)
    builder.add_edge("human_handoff", END)
    
    return builder.compile()
