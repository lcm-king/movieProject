// ========== Admin Page ==========
async function loadAdminPage() {
    if (!STATE.user) {
        showToast('请先登录', 'error');
        navigateTo('home');
        return;
    }
    if (STATE.user.role !== 'admin') {
        // Check if admin can be claimed (no admin in system)
        try {
            const res = await api.post('/api/users/claim-admin');
            // Success! Update state and reload
            setAuthData(res.data);
            showToast('已自动提升为管理员', 'success');
            switchAdminTab(STATE.adminTab);
            return;
        } catch (err) {
            // Admin already exists or other error — show access denied
            document.querySelector('#page-admin .admin-container').innerHTML = `
                <div style="text-align:center;padding:80px 24px;">
                    <p style="font-size:1.2rem;margin-bottom:16px;color:var(--text-secondary);">需要管理员权限才能访问此页面</p>
                    <button class="btn-hero" onclick="navigateTo('home')">返回首页</button>
                </div>`;
            return;
        }
    }
    switchAdminTab(STATE.adminTab);
}

function switchAdminTab(tab) {
    STATE.adminTab = tab;
    document.querySelectorAll('.admin-tab').forEach(t => {
        const labels = { users: '用户管理', movies: '电影管理', comments: '评论管理' };
        t.classList.toggle('active', t.textContent.includes(labels[tab] || ''));
    });

    ['users', 'movies', 'comments'].forEach(t => {
        const panel = document.getElementById(`adminPanel${t.charAt(0).toUpperCase() + t.slice(1)}`);
        if (panel) panel.style.display = t === tab ? 'block' : 'none';
    });

    if (tab === 'users') loadAdminUsers();
    else if (tab === 'movies') loadAdminMovies();
    else if (tab === 'comments') loadAdminComments();
}

// ── User management ───────────────────────────────────────────

async function loadAdminUsers() {
    try {
        const res = await api.get('/api/admin/users');
        const users = res.data;
        document.getElementById('adminUsersTable').innerHTML = `
            <thead><tr><th>ID</th><th>用户名</th><th>邮箱</th><th>角色</th><th>状态</th><th>操作</th></tr></thead>
            <tbody>${users.map(u => `
                <tr>
                    <td>${u.id}</td>
                    <td>${escapeHtml(u.username)}</td>
                    <td>${escapeHtml(u.email)}</td>
                    <td>${u.role === 'admin' ? '管理员' : '用户'}</td>
                    <td>${u.is_active ? '✅ 正常' : '🚫 已封禁'}</td>
                    <td>
                        ${u.id !== STATE.user.id ? `
                            ${u.is_active
                                ? `<button class="btn-action btn-ban" onclick="adminUserAction(${u.id}, 'ban')">封禁</button>`
                                : `<button class="btn-action btn-unban" onclick="adminUserAction(${u.id}, 'unban')">解封</button>`}
                            ${u.role !== 'admin'
                                ? `<button class="btn-action" style="background:var(--accent);color:#fff;" onclick="adminUserAction(${u.id}, 'set_admin')">设为管理员</button>`
                                : `<button class="btn-action" style="background:#e67e22;color:#fff;" onclick="adminUserAction(${u.id}, 'unset_admin')">取消管理员</button>`}
                        ` : '-'}
                    </td>
                </tr>`).join('')}</tbody>`;
    } catch (err) {
        showToast('加载用户列表失败', 'error');
    }
}

async function adminUserAction(userId, action) {
    const labels = { ban: '封禁', unban: '解封', set_admin: '设为管理员', unset_admin: '取消管理员' };
    const label = labels[action] || action;
    if (!confirm(`确定要${label}该用户吗？`)) return;
    try {
        await api.post('/api/admin/users/action', { user_id: userId, action });
        showToast(`用户已${label}`, 'success');
        loadAdminUsers();
    } catch (err) {
        showToast(err.response?.data?.detail || '操作失败', 'error');
    }
}

// ── Movie management ──────────────────────────────────────────

async function loadAdminMovies() {
    try {
        const res = await api.get('/api/admin/movies');
        const movies = res.data.movies;
        document.getElementById('adminMoviesTable').innerHTML = `
            <thead><tr><th>ID</th><th>标题</th><th>类型</th><th>年份</th><th>评分</th><th>评分人数</th><th>操作</th></tr></thead>
            <tbody>${movies.map(m => `
                <tr>
                    <td>${m.id}</td>
                    <td>${escapeHtml(m.title)}</td>
                    <td>${escapeHtml(m.genre)}</td>
                    <td>${m.release_year || '-'}</td>
                    <td>${m.avg_rating.toFixed(1)}</td>
                    <td>${m.rating_count}</td>
                    <td>
                        <button class="btn-action" style="background:var(--accent);color:#fff;" onclick="showMovieForm(${m.id})">编辑</button>
                        <button class="btn-action btn-delete" onclick="deleteMovie(${m.id})">删除</button>
                    </td>
                </tr>`).join('')}</tbody>`;
    } catch (err) {
        showToast('加载电影列表失败', 'error');
    }
}

function showMovieForm(movieId) {
    const isNew = !movieId;
    const modal = document.getElementById('movieFormModal');
    const titleEl = document.getElementById('movieFormTitle');
    document.getElementById('movieFormId').value = movieId || '';
    titleEl.textContent = isNew ? '添加电影' : '编辑电影';

    document.getElementById('movieTitle').value = '';
    document.getElementById('movieDescription').value = '';
    document.getElementById('movieYear').value = '';
    document.getElementById('movieCover').value = '';
    document.querySelectorAll('#movieGenresCheckboxes input').forEach(cb => cb.checked = false);

    if (!isNew) {
        api.get(`/api/movies/${movieId}`).then(res => {
            const m = res.data;
            document.getElementById('movieTitle').value = m.title;
            document.getElementById('movieDescription').value = m.description || '';
            document.getElementById('movieYear').value = m.release_year || '';
            document.getElementById('movieCover').value = m.cover_url || '';
            const genres = m.genre.split(',').map(g => g.trim());
            document.querySelectorAll('#movieGenresCheckboxes input').forEach(cb => {
                if (genres.includes(cb.value)) cb.checked = true;
            });
        }).catch(() => showToast('加载电影信息失败', 'error'));
    }

    modal.style.display = 'flex';
}

function closeMovieForm() {
    document.getElementById('movieFormModal').style.display = 'none';
}

async function saveMovie(e) {
    e.preventDefault();
    const movieId = document.getElementById('movieFormId').value;
    const title = document.getElementById('movieTitle').value.trim();
    const description = document.getElementById('movieDescription').value.trim();
    const yearVal = document.getElementById('movieYear').value;
    const coverUrl = document.getElementById('movieCover').value.trim();
    const genres = Array.from(document.querySelectorAll('#movieGenresCheckboxes input:checked')).map(cb => cb.value);

    if (!title) { showToast('请输入电影名称', 'error'); return; }
    if (genres.length === 0) { showToast('请选择至少一个类型', 'error'); return; }

    const payload = {
        title,
        description,
        cover_url: coverUrl,
        release_year: yearVal ? parseInt(yearVal) : null,
        genres,
    };

    try {
        if (movieId) {
            await api.put(`/api/admin/movies/${movieId}`, payload);
            showToast('电影已更新', 'success');
        } else {
            await api.post('/api/admin/movies', payload);
            showToast('电影已添加', 'success');
        }
        closeMovieForm();
        loadAdminMovies();
    } catch (err) {
        showToast(err.response?.data?.detail || '保存失败', 'error');
    }
}

async function deleteMovie(movieId) {
    if (!confirm('确定要删除这部电影吗？相关评分和评论也会被删除。')) return;
    try {
        await api.delete(`/api/admin/movies/${movieId}`);
        showToast('电影已删除', 'success');
        loadAdminMovies();
    } catch (err) {
        showToast(err.response?.data?.detail || '删除失败', 'error');
    }
}

// ── Comment management ────────────────────────────────────────

async function loadAdminComments() {
    try {
        const res = await api.get('/api/admin/comments');
        const comments = res.data;
        document.getElementById('adminCommentsTable').innerHTML = `
            <thead><tr><th>ID</th><th>用户</th><th>电影ID</th><th>内容</th><th>时间</th><th>操作</th></tr></thead>
            <tbody>${comments.map(c => `
                <tr>
                    <td>${c.id}</td>
                    <td>${escapeHtml(c.username || '')}</td>
                    <td>${c.movie_id}</td>
                    <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(c.content)}</td>
                    <td>${new Date(c.created_at).toLocaleString('zh-CN')}</td>
                    <td><button class="btn-action btn-delete" onclick="deleteComment(${c.id})">删除</button></td>
                </tr>`).join('')}</tbody>`;
    } catch (err) {
        showToast('加载评论列表失败', 'error');
    }
}
