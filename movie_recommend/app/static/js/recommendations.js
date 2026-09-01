// ========== Recommendations Page ==========
async function loadRecommendations() {
    if (!STATE.user) {
        document.getElementById('recommendationsGrid').innerHTML =
            '<p style="text-align:center;padding:40px;color:var(--text-secondary);">请先<a href="#" onclick="showAuthModal(\'login\')">登录</a>以获取个性化推荐</p>';
        return;
    }
    try {
        const res = await api.get('/api/recommendations/');
        const data = res.data;
        const grid = document.getElementById('recommendationsGrid');
        if (data.length === 0) {
            grid.innerHTML = '<p style="text-align:center;padding:40px;color:var(--text-secondary);">暂无推荐，去给电影评评分吧～</p>';
            return;
        }
        grid.innerHTML = data.map(item => `
            <div class="movie-card" onclick="navigateTo('movie-detail', ${item.movie.id})">
                <img class="movie-card-cover" src="${item.movie.cover_url || 'https://picsum.photos/seed/' + item.movie.id + '/400/600'}" alt="${escapeHtml(item.movie.title)}" loading="lazy">
                <div class="movie-card-info">
                    <div class="movie-card-title">${escapeHtml(item.movie.title)}</div>
                    <div class="movie-card-genre">${escapeHtml(item.movie.genre)}</div>
                    <div class="movie-card-rating">⭐ ${item.movie.avg_rating.toFixed(1)}</div>
                    <div style="font-size:0.78rem;color:var(--text-secondary);margin-top:4px;">${escapeHtml(item.reason)}</div>
                </div>
            </div>
        `).join('');
    } catch (err) {
        showToast('加载推荐失败', 'error');
    }
}
