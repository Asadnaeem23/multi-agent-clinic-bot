// ==========================================
//  ADMIN DASHBOARD LOGIC
// ==========================================

const API_BASE = `${window.location.origin}/api`;

// State
let selectedChat = null;
let allChats = [];
let allBookings = [];
let allUsers = [];

let currentMonth = new Date().getMonth();
let currentYear = new Date().getFullYear();
let selectedDate = new Date();
let allBlockouts = [];

// ==========================================
//  TOAST
// ==========================================

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, char => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    })[char]);
}

// ==========================================
//  SECTION NAVIGATION
// ==========================================

function switchSection(sectionName, navEl) {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
    // Deactivate all nav items
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    // Show target section
    const section = document.getElementById(`section-${sectionName}`);
    if (section) section.classList.add('active');
    if (navEl) navEl.classList.add('active');

    // Load data for the section
    if (sectionName === 'dashboard') loadDashboardStats();
    if (sectionName === 'chats') loadChats();
    if (sectionName === 'bookings') loadBookings();
    if (sectionName === 'calendar') loadCalendar();
    if (sectionName === 'settings') loadSettings();
}

// ==========================================
//  DASHBOARD
// ==========================================

async function loadDashboardStats() {
    try {
        const res = await fetch(`${API_BASE}/dashboard/stats`);
        if (!res.ok) throw new Error('Failed to fetch stats');
        const stats = await res.json();

        document.getElementById('stat-total-chats').textContent = stats.total_chats;
        document.getElementById('stat-active-chats').textContent = stats.active_chats;
        document.getElementById('stat-waiting-human').textContent = stats.waiting_human;
        document.getElementById('stat-todays-bookings').textContent = stats.todays_bookings;
        document.getElementById('stat-total-bookings').textContent = stats.total_bookings;
        document.getElementById('stat-scheduled-bookings').textContent = stats.scheduled_bookings;

        // Update waiting badge
        const badge = document.getElementById('waiting-badge');
        if (stats.waiting_human > 0) {
            badge.style.display = 'inline';
            badge.textContent = stats.waiting_human;
        } else {
            badge.style.display = 'none';
        }
    } catch (err) {
        console.error('Dashboard stats error:', err);
    }
}

// ==========================================
//  CHATS
// ==========================================

async function loadChats() {
    const filter = document.getElementById('chat-filter-status').value;
    try {
        const url = filter === 'all' ? `${API_BASE}/chats` : `${API_BASE}/chats?status=${filter}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error('Failed to fetch chats');
        allChats = await res.json();
        renderChatList();
    } catch (err) {
        console.error('Chats error:', err);
        document.getElementById('chat-list').innerHTML = '<p class="empty-state">Failed to load chats</p>';
    }
}

function renderChatList() {
    const list = document.getElementById('chat-list');

    if (allChats.length === 0) {
        list.innerHTML = '<p class="empty-state">No chats found</p>';
        return;
    }

    list.innerHTML = allChats.map(chat => `
        <div class="chat-item ${selectedChat && selectedChat.id === chat.id ? 'selected' : ''}" 
             onclick="selectChat(${chat.id})">
            <div class="chat-item-header">
                <span class="chat-item-title">Chat #${chat.id}</span>
                <span class="badge ${chat.status}">${chat.status.replace('_', ' ')}</span>
            </div>
            <span class="chat-item-date">${new Date(chat.updated_at).toLocaleString()}</span>
        </div>
    `).join('');
}

async function selectChat(chatId) {
    selectedChat = allChats.find(c => c.id === chatId);
    if (!selectedChat) return;

    renderChatList();

    document.getElementById('chat-detail-title').textContent = `Chat #${selectedChat.id}`;
    document.getElementById('chat-actions').style.display = 'flex';
    document.getElementById('admin-reply-bar').style.display = 'flex';

    // Load messages
    try {
        const res = await fetch(`${API_BASE}/chats/${selectedChat.thread_id}/messages`);
        if (!res.ok) throw new Error('Failed to load messages');
        const messages = await res.json();
        renderAdminMessages(messages);
    } catch (err) {
        console.error('Messages error:', err);
    }
}

function renderAdminMessages(messages) {
    const area = document.getElementById('admin-messages-area');

    if (messages.length === 0) {
        area.innerHTML = '<p class="empty-state">No messages yet</p>';
        return;
    }

    area.innerHTML = messages.map(msg => {
        const formattedContent = escapeHtml(msg.content).replace(/\n/g, '<br>');
        const agentLabel = msg.agent ? `<div class="admin-msg-agent">${escapeHtml(msg.agent)}</div>` : '';
        return `
            <div class="admin-msg-row ${msg.role}">
                <div class="admin-msg-bubble">
                    <div>${formattedContent}</div>
                    ${agentLabel}
                </div>
            </div>
        `;
    }).join('');

    // Scroll to bottom
    area.scrollTop = area.scrollHeight;
}

async function updateChatStatus(status) {
    if (!selectedChat) return;
    try {
        const res = await fetch(`${API_BASE}/chats/${selectedChat.thread_id}/status?status=${status}`, {
            method: 'PUT'
        });
        if (!res.ok) throw new Error('Failed to update status');
        showToast(`Chat status updated to ${status}`, 'success');
        selectedChat.status = status;
        loadChats();
    } catch (err) {
        console.error('Update status error:', err);
        showToast('Failed to update status', 'error');
    }
}

async function deleteChat(threadId) {
    if (!threadId) return;
    if (!confirm("Are you sure you want to completely erase this chat and all its messages? This action cannot be undone.")) return;
    
    try {
        const res = await fetch(`${API_BASE}/chats/${threadId}`, {
            method: 'DELETE'
        });
        if (!res.ok) throw new Error('Failed to delete chat');
        
        showToast('Chat successfully erased', 'success');
        
        // If the deleted chat is currently selected, clear the selection
        if (selectedChat && selectedChat.thread_id === threadId) {
            selectedChat = null;
            document.getElementById('chat-detail-title').textContent = 'Select a chat';
            document.getElementById('chat-actions').style.display = 'none';
            document.getElementById('admin-reply-bar').style.display = 'none';
            document.getElementById('admin-messages-area').innerHTML = '<p class="empty-state">Select a conversation to view messages</p>';
        }
        
        loadChats();
    } catch (err) {
        console.error('Delete chat error:', err);
        showToast('Failed to delete chat', 'error');
    }
}
async function sendAdminReply() {
    if (!selectedChat) return;
    const input = document.getElementById('admin-reply-input');
    const content = input.value.trim();
    if (!content) return;

    try {
        const res = await fetch(`${API_BASE}/chats/${selectedChat.thread_id}/admin-reply`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });
        if (!res.ok) throw new Error('Failed to send reply');
        showToast('Reply sent!', 'success');
        input.value = '';
        selectChat(selectedChat.id);
    } catch (err) {
        console.error('Reply error:', err);
        showToast('Failed to send reply', 'error');
    }
}

// ==========================================
//  BOOKINGS
// ==========================================

async function loadBookings() {
    const filter = document.getElementById('booking-filter-status').value;
    try {
        const url = filter === 'all' ? `${API_BASE}/bookings` : `${API_BASE}/bookings?status=${filter}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error('Failed to fetch bookings');
        allBookings = await res.json();
        renderBookingsTable();
    } catch (err) {
        console.error('Bookings error:', err);
        document.getElementById('bookings-tbody').innerHTML = '<tr><td colspan="7" class="empty-state">Failed to load bookings</td></tr>';
    }
}

function renderBookingsTable() {
    const tbody = document.getElementById('bookings-tbody');

    if (allBookings.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No bookings found</td></tr>';
        return;
    }

    tbody.innerHTML = allBookings.map(b => `
        <tr>
            <td>#${b.id}</td>
            <td>${escapeHtml(b.service)}</td>
            <td>${escapeHtml(b.doctor)}</td>
            <td>${new Date(b.appointment_date).toLocaleString()}</td>
            <td><span class="badge ${b.status}">${b.status}</span></td>
            <td>${b.notes ? escapeHtml(b.notes) : '—'}</td>
            <td class="actions-cell">
                <button class="btn-icon" onclick="editBooking(${b.id})" title="Edit">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                </button>
                <button class="btn-icon danger" onclick="deleteBooking(${b.id})" title="Delete">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
            </td>
        </tr>
    `).join('');
}

async function loadUsers() {
    try {
        const res = await fetch(`${API_BASE}/users`);
        if (!res.ok) throw new Error('Failed to fetch users');
        allUsers = await res.json();
    } catch (err) {
        console.error('Users error:', err);
    }
}

function openBookingModal(editId = null) {
    const modal = document.getElementById('booking-modal');
    const title = document.getElementById('booking-modal-title');

    // Populate users dropdown
    const userSelect = document.getElementById('booking-user');
    userSelect.innerHTML = '<option value="">Select User</option>';
    allUsers.forEach(u => {
        userSelect.innerHTML += `<option value="${u.id}">${escapeHtml(u.name)} (${escapeHtml(u.email)})</option>`;
    });

    if (editId) {
        title.textContent = 'Edit Booking';
        const booking = allBookings.find(b => b.id === editId);
        if (booking) {
            document.getElementById('booking-edit-id').value = booking.id;
            document.getElementById('booking-user').value = booking.user_id;
            document.getElementById('booking-service').value = booking.service;
            document.getElementById('booking-doctor').value = booking.doctor;
            document.getElementById('booking-status').value = booking.status;
            document.getElementById('booking-notes').value = booking.notes || '';
            // Format datetime for input
            const dt = new Date(booking.appointment_date);
            const local = new Date(dt.getTime() - dt.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
            document.getElementById('booking-datetime').value = local;
        }
    } else {
        title.textContent = 'New Booking';
        document.getElementById('booking-edit-id').value = '';
        document.getElementById('booking-user').value = '';
        document.getElementById('booking-service').value = '';
        document.getElementById('booking-doctor').value = '';
        document.getElementById('booking-datetime').value = '';
        document.getElementById('booking-status').value = 'scheduled';
        document.getElementById('booking-notes').value = '';
    }

    modal.style.display = 'flex';
}

function closeBookingModal() {
    document.getElementById('booking-modal').style.display = 'none';
}

function editBooking(id) {
    openBookingModal(id);
}

async function saveBooking() {
    const editId = document.getElementById('booking-edit-id').value;
    const userId = document.getElementById('booking-user').value;
    const service = document.getElementById('booking-service').value;
    const doctor = document.getElementById('booking-doctor').value;
    const datetime = document.getElementById('booking-datetime').value;
    const status = document.getElementById('booking-status').value;
    const notes = document.getElementById('booking-notes').value;

    if (!service || !doctor || !datetime) {
        showToast('Please fill in all required fields', 'error');
        return;
    }

    try {
        if (editId) {
            // Update
            const res = await fetch(`${API_BASE}/bookings/${editId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    service, doctor,
                    appointment_date: new Date(datetime).toISOString(),
                    status, notes: notes || null
                })
            });
            if (!res.ok) throw new Error('Failed to update booking');
            showToast('Booking updated!', 'success');
        } else {
            // Create
            if (!userId) {
                showToast('Please select a user', 'error');
                return;
            }
            const res = await fetch(`${API_BASE}/bookings`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: parseInt(userId),
                    service, doctor,
                    appointment_date: new Date(datetime).toISOString(),
                    notes: notes || null
                })
            });
            if (!res.ok) throw new Error('Failed to create booking');
            showToast('Booking created!', 'success');
        }

        closeBookingModal();
        loadBookings();
    } catch (err) {
        console.error('Save booking error:', err);
        showToast('Failed to save booking', 'error');
    }
}

async function deleteBooking(id) {
    if (!confirm('Are you sure you want to delete this booking?')) return;
    try {
        const res = await fetch(`${API_BASE}/bookings/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Failed to delete booking');
        showToast('Booking deleted', 'success');
        loadBookings();
    } catch (err) {
        console.error('Delete booking error:', err);
        showToast('Failed to delete booking', 'error');
    }
}

// ==========================================
//  SETTINGS
// ==========================================

async function loadSettings() {
    try {
        const [contextRes, configRes] = await Promise.all([
            fetch(`${API_BASE}/settings/context`),
            fetch(`${API_BASE}/settings/config`)
        ]);

        if (!contextRes.ok || !configRes.ok) throw new Error('Failed to load settings data');

        const contextData = await contextRes.json();
        document.getElementById('business-context-textarea').value = contextData.business_context;

        const configData = await configRes.json();
        document.getElementById('cfg-clear-empty-keys').checked = false;
        
        document.getElementById('cfg-openrouter-site-url').value = configData.openrouter_site_url || '';
        document.getElementById('cfg-openrouter-app-name').value = configData.openrouter_app_name || '';
        setSecretPlaceholder('cfg-groq-api-key', configData.groq_api_key_configured);
        setSecretPlaceholder('cfg-openrouter-api-key', configData.openrouter_api_key_configured);

        ['supervisor', 'inquiry', 'booking', 'human-handoff', 'guardrail'].forEach(agent => {
            const configName = agent.replace('-', '_');
            document.getElementById(`cfg-provider-${agent}`).value = configData[`provider_${configName}`] || 'groq';
        });
        
        // Populate Models
        populateModelSetting('supervisor', configData.model_supervisor);
        populateModelSetting('inquiry', configData.model_inquiry);
        populateModelSetting('booking', configData.model_booking);
        populateModelSetting('human-handoff', configData.model_human_handoff);
        populateModelSetting('guardrail', configData.model_guardrail);

        ['supervisor', 'inquiry', 'booking', 'human-handoff', 'guardrail'].forEach(agent => {
            const configName = agent.replace('-', '_');
            setSecretPlaceholder(`cfg-apikey-${agent}`, configData[`api_key_${configName}_configured`]);
        });

        document.getElementById('cfg-guardrails-enabled').checked = configData.guardrails_enabled;
        document.getElementById('cfg-guardrail-heuristics-enabled').checked = configData.guardrail_heuristics_enabled;
        document.getElementById('cfg-guardrail-failure-mode').value = configData.guardrail_failure_mode;
        document.getElementById('cfg-guardrail-system-prompt').value = configData.guardrail_system_prompt;
        document.getElementById('cfg-guardrail-injection-response').value = configData.guardrail_injection_response;
        document.getElementById('cfg-guardrail-irrelevant-response').value = configData.guardrail_irrelevant_response;
        document.getElementById('cfg-guardrail-failure-response').value = configData.guardrail_failure_response;

    } catch (err) {
        console.error('Settings load error:', err);
        showToast('Failed to load settings', 'error');
    }
}

function setSecretPlaceholder(elementId, configured) {
    const input = document.getElementById(elementId);
    input.value = '';
    input.placeholder = configured ? 'Saved — enter a new value to replace it' : 'No key saved';
}

function populateModelSetting(agent, value) {
    const select = document.getElementById(`cfg-model-${agent}`);
    const customInput = document.getElementById(`cfg-model-${agent}-custom`);
    
    if (!select || !customInput) return;
    
    let found = false;
    for (let opt of select.options) {
        if (opt.value === value) {
            select.value = value;
            found = true;
            break;
        }
    }
    
    if (!found && value) {
        select.value = 'custom';
        customInput.value = value;
        customInput.classList.remove('hidden');
    } else {
        customInput.classList.add('hidden');
        customInput.value = '';
    }
}

function toggleCustomModel(agent) {
    const select = document.getElementById(`cfg-model-${agent}`);
    const customInput = document.getElementById(`cfg-model-${agent}-custom`);
    if (select.value === 'custom') {
        customInput.classList.remove('hidden');
    } else {
        customInput.classList.add('hidden');
    }
}

async function saveLLMConfig() {
    const getModelValue = (agent) => {
        const select = document.getElementById(`cfg-model-${agent}`);
        const customInput = document.getElementById(`cfg-model-${agent}-custom`);
        if (select.value === 'custom') {
            return customInput.value.trim();
        }
        return select.value;
    };
    
    const supervisor = getModelValue('supervisor');
    const inquiry = getModelValue('inquiry');
    const booking = getModelValue('booking');
    const humanHandoff = getModelValue('human-handoff');
    const guardrail = getModelValue('guardrail');
    
    if (!supervisor || !inquiry || !booking || !humanHandoff || !guardrail) {
        showToast('All agent models must be configured', 'error');
        return;
    }

    const requiredTextIds = [
        'cfg-guardrail-system-prompt', 'cfg-guardrail-injection-response',
        'cfg-guardrail-irrelevant-response', 'cfg-guardrail-failure-response'
    ];
    if (requiredTextIds.some(id => !document.getElementById(id).value.trim())) {
        showToast('Guardrail prompt and reply messages cannot be blank', 'error');
        return;
    }

    const clearEmptySecrets = document.getElementById('cfg-clear-empty-keys').checked;
    const optionalSecret = id => {
        const value = document.getElementById(id).value.trim();
        return value || (clearEmptySecrets ? '' : null);
    };
    const provider = agent => document.getElementById(`cfg-provider-${agent}`).value;
    
    try {
        const res = await fetch(`${API_BASE}/settings/config`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                groq_api_key: optionalSecret('cfg-groq-api-key'),
                openrouter_api_key: optionalSecret('cfg-openrouter-api-key'),
                openrouter_site_url: document.getElementById('cfg-openrouter-site-url').value.trim(),
                openrouter_app_name: document.getElementById('cfg-openrouter-app-name').value.trim() || 'AI Customer Support',
                provider_supervisor: provider('supervisor'),
                provider_inquiry: provider('inquiry'),
                provider_booking: provider('booking'),
                provider_human_handoff: provider('human-handoff'),
                provider_guardrail: provider('guardrail'),
                model_supervisor: supervisor,
                model_inquiry: inquiry,
                model_booking: booking,
                model_human_handoff: humanHandoff,
                model_guardrail: guardrail,
                api_key_supervisor: optionalSecret('cfg-apikey-supervisor'),
                api_key_inquiry: optionalSecret('cfg-apikey-inquiry'),
                api_key_booking: optionalSecret('cfg-apikey-booking'),
                api_key_human_handoff: optionalSecret('cfg-apikey-human-handoff'),
                api_key_guardrail: optionalSecret('cfg-apikey-guardrail'),
                guardrails_enabled: document.getElementById('cfg-guardrails-enabled').checked,
                guardrail_heuristics_enabled: document.getElementById('cfg-guardrail-heuristics-enabled').checked,
                guardrail_failure_mode: document.getElementById('cfg-guardrail-failure-mode').value,
                guardrail_system_prompt: document.getElementById('cfg-guardrail-system-prompt').value.trim(),
                guardrail_injection_response: document.getElementById('cfg-guardrail-injection-response').value.trim(),
                guardrail_irrelevant_response: document.getElementById('cfg-guardrail-irrelevant-response').value.trim(),
                guardrail_failure_response: document.getElementById('cfg-guardrail-failure-response').value.trim()
            })
        });
        
        if (!res.ok) throw new Error(await res.text());
        showToast('API & LLM Configuration saved successfully!', 'success');
        loadSettings();
    } catch (err) {
        console.error('Save config error:', err);
        showToast('Failed to save configurations', 'error');
    }
}

async function testGuardrails() {
    const message = document.getElementById('guardrail-test-message').value.trim();
    const result = document.getElementById('guardrail-test-result');
    if (!message) {
        showToast('Enter a message to test', 'error');
        return;
    }
    result.textContent = 'Testing...';
    try {
        const res = await fetch(`${API_BASE}/settings/guardrails/test`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        result.textContent = `${data.decision.toUpperCase()} — ${data.reason} (${data.source})`;
    } catch (err) {
        console.error('Guardrail test error:', err);
        result.textContent = 'Test failed. Check the provider, API key, and model settings.';
    }
}


async function saveSettings() {
    const context = document.getElementById('business-context-textarea').value;
    try {
        const res = await fetch(`${API_BASE}/settings/context`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ business_context: context })
        });
        if (!res.ok) throw new Error('Failed to save');
        showToast('Business settings saved!', 'success');
    } catch (err) {
        console.error('Save settings error:', err);
        showToast('Failed to save settings', 'error');
    }
}

async function resetSettings() {
    if (!confirm('Reset to default settings? This will overwrite your current business context.')) return;
    try {
        const res = await fetch(`${API_BASE}/settings/reset`, { method: 'POST' });
        if (!res.ok) throw new Error('Failed to reset');
        showToast('Settings reset to default', 'success');
        loadSettings();
    } catch (err) {
        console.error('Reset settings error:', err);
        showToast('Failed to reset settings', 'error');
    }
}

// ==========================================
//  CALENDAR & BLOCKOUTS
// ==========================================

async function loadCalendar() {
    try {
        const [bookingsRes, blockoutsRes] = await Promise.all([
            fetch(`${API_BASE}/bookings`),
            fetch(`${API_BASE}/blockouts`)
        ]);

        if (!bookingsRes.ok || !blockoutsRes.ok) throw new Error('Failed to fetch calendar data');

        allBookings = await bookingsRes.json();
        allBlockouts = await blockoutsRes.json();

        renderCalendarGrid();
        renderDailyDetail();
    } catch (err) {
        console.error('Calendar load error:', err);
        showToast('Failed to load calendar data', 'error');
    }
}

const MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
];

function changeMonth(offset) {
    currentMonth += offset;
    if (currentMonth < 0) {
        currentMonth = 11;
        currentYear--;
    } else if (currentMonth > 11) {
        currentMonth = 0;
        currentYear++;
    }
    renderCalendarGrid();
}

function renderCalendarGrid() {
    document.getElementById('calendar-month-year').textContent = `${MONTH_NAMES[currentMonth]} ${currentYear}`;

    const grid = document.getElementById('calendar-days-grid');
    grid.innerHTML = '';

    const firstDay = new Date(currentYear, currentMonth, 1).getDay();
    const totalDays = new Date(currentYear, currentMonth + 1, 0).getDate();

    for (let i = 0; i < firstDay; i++) {
        grid.innerHTML += `<div class="calendar-day empty"></div>`;
    }

    const todayStr = new Date().toDateString();

    for (let day = 1; day <= totalDays; day++) {
        const dateObj = new Date(currentYear, currentMonth, day);
        const dateStr = dateObj.toDateString();
        const dateISO = dateObj.toLocaleDateString('sv').split(' ')[0]; // YYYY-MM-DD local safe format

        const dayBookings = allBookings.filter(b => {
            const bDate = new Date(b.appointment_date).toLocaleDateString('sv').split(' ')[0];
            return bDate === dateISO && b.status !== 'cancelled';
        });

        const dayBlockouts = allBlockouts.filter(bl => {
            const blDate = new Date(bl.start_time).toLocaleDateString('sv').split(' ')[0];
            return blDate === dateISO;
        });

        const isToday = dateStr === todayStr;
        const isSelected = selectedDate && selectedDate.toDateString() === dateStr;

        let indicators = '';
        if (dayBookings.length > 0) {
            indicators += `<span class="indicator booking-ind">${dayBookings.length} Booking${dayBookings.length > 1 ? 's' : ''}</span>`;
        }
        if (dayBlockouts.length > 0) {
            indicators += `<span class="indicator blockout-ind">${dayBlockouts.length} Blocked</span>`;
        }

        const borderStyle = isSelected ? 'border-color: var(--primary);' : '';

        grid.innerHTML += `
            <div class="calendar-day ${isToday ? 'today' : ''}" style="${borderStyle}" onclick="selectDate(${currentYear}, ${currentMonth}, ${day})">
                <span class="calendar-day-num">${day}</span>
                <div class="calendar-day-indicators">
                    ${indicators}
                </div>
            </div>
        `;
    }
}

function selectDate(year, month, day) {
    selectedDate = new Date(year, month, day);
    renderCalendarGrid();
    renderDailyDetail();
}

function renderDailyDetail() {
    if (!selectedDate) return;

    const labelStr = selectedDate.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    document.getElementById('selected-date-label').textContent = labelStr;

    const container = document.getElementById('daily-timeline');
    const selectedISO = selectedDate.toLocaleDateString('sv').split(' ')[0];

    const dayBookings = allBookings.filter(b => {
        return new Date(b.appointment_date).toLocaleDateString('sv').split(' ')[0] === selectedISO;
    });

    const dayBlockouts = allBlockouts.filter(bl => {
        return new Date(bl.start_time).toLocaleDateString('sv').split(' ')[0] === selectedISO;
    });

    if (dayBookings.length === 0 && dayBlockouts.length === 0) {
        container.innerHTML = '<p class="empty-state">No appointments or blocked slots for this day.</p>';
        return;
    }

    const items = [];
    dayBookings.forEach(b => {
        items.push({
            type: 'booking',
            time: new Date(b.appointment_date),
            title: `${b.service} - ${b.doctor}`,
            desc: `Patient ID: #${b.user_id} | Status: ${b.status} ${b.notes ? '| Notes: ' + b.notes : ''}`,
            id: b.id
        });
    });

    dayBlockouts.forEach(bl => {
        items.push({
            type: 'blockout',
            time: new Date(bl.start_time),
            endTime: new Date(bl.end_time),
            title: `BLOCKED: ${bl.reason || 'Unavailable'}`,
            desc: `Doctor: ${bl.doctor || 'All'}`,
            id: bl.id
        });
    });

    items.sort((a, b) => a.time - b.time);

    container.innerHTML = items.map(item => {
        const timeStr = item.time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const endTimeStr = item.endTime ? ` - ${item.endTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : '';
        
        let actionBtn = '';
        if (item.type === 'blockout') {
            actionBtn = `
                <button class="btn-icon danger" onclick="deleteBlockout(${item.id})" title="Delete Blockout">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
            `;
        }

        return `
            <div class="timeline-slot ${item.type}">
                <div class="slot-time">
                    <span>${timeStr}</span>
                    <span>${endTimeStr}</span>
                </div>
                <div class="slot-content">
                    <div>
                        <div class="slot-title">${escapeHtml(item.title)}</div>
                        <div class="slot-desc">${escapeHtml(item.desc)}</div>
                    </div>
                    ${actionBtn}
                </div>
            </div>
        `;
    }).join('');
}

function openBlockoutModal() {
    const modal = document.getElementById('blockout-modal');
    document.getElementById('blockout-reason').value = '';
    
    const year = selectedDate.getFullYear();
    const month = String(selectedDate.getMonth() + 1).padStart(2, '0');
    const day = String(selectedDate.getDate()).padStart(2, '0');
    
    document.getElementById('blockout-start').value = `${year}-${month}-${day}T13:00`;
    document.getElementById('blockout-end').value = `${year}-${month}-${day}T14:00`;

    modal.style.display = 'flex';
}

function closeBlockoutModal() {
    document.getElementById('blockout-modal').style.display = 'none';
}

async function saveBlockout() {
    const doctor = document.getElementById('blockout-doctor').value;
    const start = document.getElementById('blockout-start').value;
    const end = document.getElementById('blockout-end').value;
    const reason = document.getElementById('blockout-reason').value.trim();

    if (!start || !end) {
        showToast('Please fill in start and end times', 'error');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/blockouts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                doctor,
                start_time: new Date(start).toISOString(),
                end_time: new Date(end).toISOString(),
                reason: reason || null
            })
        });

        if (!res.ok) throw new Error('Failed to save blockout');
        showToast('Time slot blocked successfully!', 'success');
        closeBlockoutModal();
        loadCalendar();
    } catch (err) {
        console.error('Save blockout error:', err);
        showToast('Failed to save blockout', 'error');
    }
}

async function deleteBlockout(id) {
    if (!confirm('Are you sure you want to remove this blockout slot?')) return;
    try {
        const res = await fetch(`${API_BASE}/blockouts/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Failed to delete blockout');
        showToast('Blockout removed', 'success');
        loadCalendar();
    } catch (err) {
        console.error('Delete blockout error:', err);
        showToast('Failed to remove blockout', 'error');
    }
}

// ==========================================
//  INIT
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    loadDashboardStats();
    loadUsers();
});
