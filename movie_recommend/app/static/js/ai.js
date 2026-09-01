// ========== Unified AI Chat ==========

function loadAIPage() {
    // No special init needed — the chat HTML is static
    // Focus input on load
    setTimeout(() => document.getElementById('chatInput')?.focus(), 300);
}

function handleChatKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChatMessage();
    }
}

async function sendChatMessage() {
    if (!STATE.user) { showToast('请先登录', 'error'); return; }

    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message) return;

    // Add user message
    appendMessage('user', message);
    input.value = '';
    input.style.height = 'auto';

    // Show typing indicator
    const typingId = showTyping();

    try {
        const res = await api.post('/api/ai/chat', { message });
        // Remove typing indicator
        removeTyping(typingId);
        appendMessage('assistant', res.data.reply);
    } catch (err) {
        removeTyping(typingId);
        appendMessage('assistant', '😅 抱歉，我暂时无法回答，请稍后重试。');
    }
}

function appendMessage(role, text) {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = `chat-message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'chat-avatar';
    avatar.textContent = role === 'user' ? '👤' : '🤖';

    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';
    // Render markdown-like formatting: **bold** and \n
    const html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');
    bubble.innerHTML = html;

    div.appendChild(avatar);
    div.appendChild(bubble);
    container.appendChild(div);

    scrollToBottom();
}

function showTyping() {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = 'chat-message assistant typing-indicator';
    div.id = 'typing-' + Date.now();

    const avatar = document.createElement('div');
    avatar.className = 'chat-avatar';
    avatar.textContent = '🤖';

    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';
    bubble.innerHTML = '<span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>';

    div.appendChild(avatar);
    div.appendChild(bubble);
    container.appendChild(div);
    scrollToBottom();

    return div.id;
}

function removeTyping(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function scrollToBottom() {
    const container = document.getElementById('chatMessages');
    container.scrollTop = container.scrollHeight;
}
