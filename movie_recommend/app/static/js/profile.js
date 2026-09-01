// ========== Profile Page ==========
async function loadProfilePage() {
    if (!STATE.user) {
        document.getElementById('profileContent').innerHTML =
            '<p style="text-align:center;padding:40px;">请先<a href="#" onclick="showAuthModal(\'login\')">登录</a></p>';
        return;
    }
    try {
        const res = await api.get('/api/users/me');
        const user = res.data;
        const currentGenres = user.preferred_genres ? user.preferred_genres.split(',').filter(g => g) : [];
        document.getElementById('profileContent').innerHTML = `
            <div class="profile-card">
                <h3>基本信息</h3>
                <div class="profile-field"><label>用户名</label><span>${escapeHtml(user.username)}</span></div>
                <div class="profile-field"><label>邮箱</label><span>${escapeHtml(user.email)}</span></div>
                <div class="profile-field"><label>角色</label><span>${user.role === 'admin' ? '管理员' : '普通用户'}</span></div>
                <div class="profile-field"><label>注册时间</label><span>${new Date(user.created_at).toLocaleString('zh-CN')}</span></div>
                <h3 style="margin-top:24px;">偏好类型</h3>
                <div class="filter-genres" id="profileGenres" style="margin-bottom:16px;">
                    ${ALL_GENRES.map(g => {
                        const sel = currentGenres.includes(g) ? ' selected' : '';
                        return `<button class="filter-genre-chip${sel}" data-genre="${g}" onclick="this.classList.toggle('selected')">${g}</button>`;
                    }).join('')}
                </div>
                <button class="btn-submit" onclick="saveProfileGenres()">保存偏好</button>
            </div>`;
    } catch (err) {
        showToast('加载个人信息失败', 'error');
    }
}

async function saveProfileGenres() {
    const selected = Array.from(document.querySelectorAll('#profileGenres .filter-genre-chip.selected')).map(b => b.dataset.genre);
    if (selected.length === 0) { showToast('请至少选择一个类型', 'error'); return; }
    try {
        await api.put('/api/users/me/genres', { preferred_genres: selected });
        showToast('偏好已更新', 'success');
    } catch (err) {
        showToast('更新失败', 'error');
    }
}
