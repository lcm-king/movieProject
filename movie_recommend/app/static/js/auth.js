// ========== Authentication ==========
let authMode = 'login';

function showAuthModal(mode) {
    authMode = mode;
    document.getElementById('authModalTitle').textContent = mode === 'login' ? '登录' : '注册';
    document.getElementById('authSubmitBtn').textContent = mode === 'login' ? '登录' : '注册';
    document.getElementById('authEmailGroup').style.display = mode === 'register' ? 'block' : 'none';
    document.getElementById('authGenresGroup').style.display = mode === 'register' ? 'block' : 'none';
    document.getElementById('authSwitch').innerHTML = mode === 'login'
        ? '还没有账号？<a href="#" onclick="switchAuthMode(\'register\')">立即注册</a>'
        : '已有账号？<a href="#" onclick="switchAuthMode(\'login\')">立即登录</a>';
    document.getElementById('authForm').reset();

    if (mode === 'register') {
        const container = document.getElementById('authGenresCheckboxes');
        container.innerHTML = ALL_GENRES.map(g =>
            `<label><input type="checkbox" value="${g}"><span>${g}</span></label>`
        ).join('');
    }

    document.getElementById('authModal').style.display = 'flex';
}

function closeAuthModal() {
    document.getElementById('authModal').style.display = 'none';
}

function switchAuthMode(mode) {
    authMode = mode;
    showAuthModal(mode);
}

async function handleAuth(e) {
    e.preventDefault();
    const username = document.getElementById('authUsername').value.trim();
    const password = document.getElementById('authPassword').value;

    if (authMode === 'login') {
        try {
            const res = await api.post('/api/users/login', { username, password });
            setAuthData(res.data);
            closeAuthModal();
            showToast('登录成功', 'success');
            navigateTo('home');
        } catch (err) {
            showToast(err.response?.data?.detail || '登录失败', 'error');
        }
    } else {
        const email = document.getElementById('authEmail').value.trim();
        const checked = document.querySelectorAll('#authGenresCheckboxes input:checked');
        const genres = Array.from(checked).map(cb => cb.value);
        if (genres.length === 0) {
            showToast('请至少选择一个偏好类型', 'error');
            return;
        }
        try {
            const res = await api.post('/api/users/register', { username, email, password, preferred_genres: genres });
            setAuthData(res.data);
            closeAuthModal();
            showToast('注册成功', 'success');
            navigateTo('home');
        } catch (err) {
            showToast(err.response?.data?.detail || '注册失败', 'error');
        }
    }
}

function setAuthData(data) {
    STATE.user = { id: data.user_id, username: data.username, role: data.role };
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('user', JSON.stringify(STATE.user));
    updateNavUI();
}

function logout() {
    STATE.user = null;
    localStorage.clear();
    updateNavUI();
    navigateTo('home');
    showToast('已退出登录', 'info');
}

function updateNavUI() {
    const loggedOut = document.getElementById('navUser');
    const loggedIn = document.getElementById('navUserLoggedIn');
    const adminLink = document.getElementById('navAdminLink');
    const usernameSpan = document.getElementById('navUsername');

    if (STATE.user) {
        loggedOut.style.display = 'none';
        loggedIn.style.display = 'flex';
        usernameSpan.textContent = STATE.user.username;
        adminLink.style.display = STATE.user.role === 'admin' ? 'inline' : 'none';
    } else {
        loggedOut.style.display = 'flex';
        loggedIn.style.display = 'none';
        adminLink.style.display = 'none';
    }
}

function toggleUserMenu() {
    const menu = document.getElementById('userDropdown');
    menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
}

document.addEventListener('click', (e) => {
    const menu = document.getElementById('userDropdown');
    const trigger = document.getElementById('userMenuTrigger');
    if (menu && trigger && !trigger.contains(e.target) && !menu.contains(e.target)) {
        menu.style.display = 'none';
    }
});
