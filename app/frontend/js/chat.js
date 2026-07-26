// ==========================================
//  CHAT LOGIC — Bright Smile Dental Chatbot
// ==========================================

const API_BASE = 'http://localhost:8001/api';

// State
let threadId = null;
let userName = '';
let userEmail = '';
let isLoading = false;

// DOM Elements
const introScreen = document.getElementById('intro-screen');
const chatScreen = document.getElementById('chat-screen');
const messagesArea = document.getElementById('messages-area');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const nameInput = document.getElementById('user-name');
const emailInput = document.getElementById('user-email');

// ==========================================
//  TOAST NOTIFICATIONS
// ==========================================

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

// ==========================================
//  INTRO → CHAT TRANSITION
// ==========================================

function startChat() {
    userName = nameInput.value.trim();
    userEmail = emailInput.value.trim();

    if (!userName || !userEmail) {
        showToast('Please enter your name and email', 'error');
        return;
    }

    // Simple email validation
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(userEmail)) {
        showToast('Please enter a valid email address', 'error');
        return;
    }

    introScreen.classList.add('hidden');
    chatScreen.classList.remove('hidden');

    // Welcome message
    addMessage('assistant', 'Hello! 👋 I\'m your AI assistant at Bright Smile Dental. How can I help you today?\n\nI can answer questions about our services, help you book appointments, or connect you with our team.', null);
}

// Enter key on intro form
nameInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') emailInput.focus();
});

emailInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') startChat();
});

// ==========================================
//  MESSAGE RENDERING
// ==========================================

function addMessage(role, content, agent) {
    const row = document.createElement('div');
    row.className = `message-row ${role}`;

    let agentBadge = '';
    if (agent) {
        agentBadge = `<div class="message-agent">${agent}</div>`;
    }

    // Convert newlines to <br> for display
    const formattedContent = content.replace(/\n/g, '<br>');

    row.innerHTML = `
        <div class="message-bubble">
            <div>${formattedContent}</div>
            ${agentBadge}
        </div>
    `;

    messagesArea.appendChild(row);
    scrollToBottom();
}

function showTyping() {
    const el = document.createElement('div');
    el.className = 'typing-indicator';
    el.id = 'typing-indicator';
    el.innerHTML = `
        <div class="typing-bubble">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    messagesArea.appendChild(el);
    scrollToBottom();
}

function hideTyping() {
    const el = document.getElementById('typing-indicator');
    if (el) el.remove();
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        messagesArea.scrollTop = messagesArea.scrollHeight;
    });
}

// ==========================================
//  SEND MESSAGE
// ==========================================

async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text || isLoading) return;

    // Add user message to UI
    addMessage('user', text, null);
    chatInput.value = '';
    updateSendBtn();

    isLoading = true;
    showTyping();
    sendBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                thread_id: threadId,
                user_name: userName,
                user_email: userEmail
            })
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();

        // Save thread ID for conversation continuity
        if (!threadId) {
            threadId = data.thread_id;
        }

        hideTyping();
        addMessage('assistant', data.content, data.agent);

        if (data.chat_status === 'waiting_human') {
            showToast('A team member will be with you shortly!', 'success');
        }

    } catch (error) {
        console.error('Chat error:', error);
        hideTyping();
        showToast('Failed to send message. Please try again.', 'error');
    } finally {
        isLoading = false;
        updateSendBtn();
    }
}

// ==========================================
//  INPUT HANDLERS
// ==========================================

chatInput.addEventListener('input', updateSendBtn);
chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

function updateSendBtn() {
    sendBtn.disabled = !chatInput.value.trim() || isLoading;
}
