// ========== Home Page ==========
async function loadHomePage() {
    try {
        const res = await api.get('/api/movies/', { params: { page: 1, page_size: 8 } });
        const container = document.getElementById('homeFeatured');
        container.innerHTML = '<h2>热门电影</h2>';
        const grid = document.createElement('div');
        grid.className = 'movies-grid';
        grid.innerHTML = res.data.movies.map(m => renderMovieCard(m)).join('');
        container.appendChild(grid);
    } catch (err) { /* non-critical */ }
}

// ========== Movies List Page ==========
function initGenreFilters() {
    const container = document.getElementById('filterGenres');
    if (!container) return;
    container.innerHTML = ALL_GENRES.map(g =>
        `<button class="filter-genre-chip" data-genre="${g}" onclick="toggleGenreFilter(this)">${g}</button>`
    ).join('');
}

function toggleGenreFilter(btn) {
    btn.classList.toggle('selected');
}

async function loadMoviesPage() {
    const genres = Array.from(document.querySelectorAll('.filter-genre-chip.selected')).map(b => b.dataset.genre);
    const params = { page: STATE.moviePage, page_size: 12 };
    if (genres.length > 0) params.genres = genres.join(',');
    if (STATE.movieFilters.search) params.search = STATE.movieFilters.search;

    const ratingMin = document.getElementById('filterRatingMin')?.value;
    const ratingMax = document.getElementById('filterRatingMax')?.value;
    const yearFrom = document.getElementById('filterYearFrom')?.value;
    const yearTo = document.getElementById('filterYearTo')?.value;
    if (ratingMin) params.rating_min = parseFloat(ratingMin);
    if (ratingMax) params.rating_max = parseFloat(ratingMax);
    if (yearFrom) params.year_from = parseInt(yearFrom);
    if (yearTo) params.year_to = parseInt(yearTo);

    try {
        const res = await api.get('/api/movies/', { params });
        STATE.moviesData = res.data.movies;
        STATE.moviesTotal = res.data.total;
        renderMoviesGrid();
        renderPagination();
    } catch (err) {
        showToast('加载电影列表失败', 'error');
    }
}

function renderMoviesGrid() {
    const grid = document.getElementById('moviesGrid');
    if (!grid) return;
    if (STATE.moviesData.length === 0) {
        grid.innerHTML = '<p style="text-align:center;color:var(--text-secondary);padding:40px;">没有找到匹配的电影</p>';
    } else {
        grid.innerHTML = STATE.moviesData.map(m => renderMovieCard(m)).join('');
    }
}

function renderPagination() {
    const totalPages = Math.ceil(STATE.moviesTotal / 12);
    const container = document.getElementById('moviesPagination');
    if (!container) return;
    if (totalPages <= 1) { container.innerHTML = ''; return; }

    let html = `<button ${STATE.moviePage <= 1 ? 'disabled' : ''} onclick="goToPage(${STATE.moviePage - 1})">上一页</button>`;
    const start = Math.max(1, STATE.moviePage - 2);
    const end = Math.min(totalPages, STATE.moviePage + 2);
    for (let i = start; i <= end; i++) {
        html += `<button class="${i === STATE.moviePage ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
    }
    html += `<button ${STATE.moviePage >= totalPages ? 'disabled' : ''} onclick="goToPage(${STATE.moviePage + 1})">下一页</button>`;
    container.innerHTML = html;
}

function goToPage(page) {
    STATE.moviePage = page;
    loadMoviesPage();
    window.scrollTo({ top: 200, behavior: 'smooth' });
}

function applyMovieFilters() {
    STATE.moviePage = 1;
    // Clear stale search from nav so sidebar filter works independently
    STATE.movieFilters = {};
    loadMoviesPage();
}

function resetMovieFilters() {
    STATE.moviePage = 1;
    STATE.movieFilters = {};
    document.getElementById('filterRatingMin').value = '';
    document.getElementById('filterRatingMax').value = '';
    document.getElementById('filterYearFrom').value = '';
    document.getElementById('filterYearTo').value = '';
    document.querySelectorAll('.filter-genre-chip').forEach(b => b.classList.remove('selected'));
    loadMoviesPage();
}

// ========== Movie Detail Page ==========
async function loadMovieDetail(movieId) {
    if (!movieId) return;
    STATE.currentMovieId = movieId;
    try {
        const [movieRes, commentsRes, distRes] = await Promise.all([
            api.get(`/api/movies/${movieId}`),
            api.get(`/api/comments/movie/${movieId}`),
            api.get(`/api/movies/${movieId}/rating-distribution`),
        ]);

        const movie = movieRes.data;
        const comments = commentsRes.data;
        const dist = distRes.data;

        let myRating = null;
        if (STATE.user) {
            try {
                const rRes = await api.get(`/api/ratings/my/${movieId}`);
                myRating = rRes.data.rating;
            } catch (e) { /* no rating yet */ }
        }

        const container = document.getElementById('movieDetail');
        const coverUrl = movie.cover_url || `https://picsum.photos/seed/${movie.id}/400/600`;

        let html = `
            <button class="btn-back" onclick="navigateTo('movies')">← 返回电影库</button>
            <div class="movie-detail-header">
                <img class="movie-detail-cover" src="${coverUrl}" alt="${escapeHtml(movie.title)}">
                <div class="movie-detail-info">
                    <h1>${escapeHtml(movie.title)}</h1>
                    <p class="meta">${escapeHtml(movie.genre)} · ${movie.release_year || '未知'} · 平均评分 ${movie.avg_rating.toFixed(1)} (${movie.rating_count}人评价)</p>
                    <button class="btn-ai-qa" onclick="navigateToAIMovieQA(${movie.id}, '${escapeHtml(movie.title).replace(/'/g, "\\'")}')">🤖 AI 问答</button>
                    <p class="description">${escapeHtml(movie.description || '暂无简介')}</p>
                    <div class="rating-bar-container">
                        <h4>评分分布</h4>
                        ${renderRatingDistribution(dist, movie.rating_count)}
                    </div>
                </div>
            </div>`;

        if (STATE.user) {
            html += `<div class="rating-section">
                <h4>${myRating ? `你的评分: ${myRating}分 (点击修改)` : '给这部电影评分'}</h4>
                <div class="rating-stars">${renderStars(movie.id, myRating)}</div>
            </div>`;
        } else {
            html += `<p style="color:var(--text-secondary);margin:16px 0;"><a href="#" onclick="showAuthModal('login')">登录</a>后即可评分和评论</p>`;
        }

        html += `<div class="comments-section"><h3>评论 (${comments.length})</h3>`;
        if (STATE.user) {
            html += `<div class="comment-form">
                <textarea id="commentInput" placeholder="写下你的评论（不超过500字）" maxlength="500" rows="3"></textarea>
                <button class="btn-submit-comment" onclick="submitComment(${movie.id})">发表评论</button>
            </div>`;
        }
        html += `<div class="comments-list" id="commentsList">${renderComments(comments, STATE.user)}</div></div>`;
        container.innerHTML = html;
    } catch (err) {
        showToast('加载电影详情失败', 'error');
    }
}

function renderRatingDistribution(dist, total) {
    let html = '';
    const maxCount = Math.max(1, ...Object.values(dist));
    for (let i = 10; i >= 1; i--) {
        const count = dist[i.toString()] || 0;
        const pct = Math.round((count / maxCount) * 100);
        html += `<div class="rating-bar-row">
            <span>${i}分</span>
            <div class="bar"><div class="bar-fill" style="width:${pct}%"></div></div>
            <span class="count">${count}</span>
        </div>`;
    }
    return html;
}

function renderStars(movieId, currentRating) {
    let html = '';
    for (let i = 1; i <= 10; i++) {
        const filled = currentRating && i <= currentRating ? '★' : '☆';
        const color = currentRating && i <= currentRating ? 'color:#ff9800' : '';
        html += `<span class="star" style="${color};font-size:${i === currentRating ? '2.2rem' : '2rem'}" onclick="rateMovie(${movieId}, ${i})">${filled}</span>`;
    }
    return html;
}

function renderComments(comments, currentUser) {
    if (comments.length === 0) return '<p style="color:var(--text-secondary);">暂无评论</p>';
    return comments.map(c => {
        const cls = c.sentiment
            ? (c.sentiment === '正面' ? 'sentiment-positive' : c.sentiment === '负面' ? 'sentiment-negative' : 'sentiment-neutral')
            : '';
        const canDelete = currentUser && (currentUser.role === 'admin' || currentUser.id === c.user_id);
        return `<div class="comment-item">
            <div class="comment-header">
                <span class="comment-user">${escapeHtml(c.username || '匿名')}</span>
                <span class="comment-time">${new Date(c.created_at).toLocaleString('zh-CN')}</span>
            </div>
            <div class="comment-content">${escapeHtml(c.content)}</div>
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                ${c.sentiment ? `<span class="comment-sentiment ${cls}">${escapeHtml(c.sentiment)}</span>` : ''}
                ${canDelete ? `<button class="btn-delete-comment" onclick="deleteComment(${c.id})">删除</button>` : ''}
            </div>
        </div>`;
    }).join('');
}

async function rateMovie(movieId, rating) {
    if (!STATE.user) { showToast('请先登录', 'error'); showAuthModal('login'); return; }
    try {
        await api.post('/api/ratings/', { movie_id: movieId, rating });
        showToast(`已评分 ${rating} 分`, 'success');
        loadMovieDetail(movieId);
    } catch (err) {
        showToast(err.response?.data?.detail || '评分失败', 'error');
    }
}

async function submitComment(movieId) {
    if (!STATE.user) { showToast('请先登录', 'error'); return; }
    const input = document.getElementById('commentInput');
    const content = input.value.trim();
    if (!content) { showToast('评论内容不能为空', 'error'); return; }
    if (content.length > 500) { showToast('评论不能超过500字', 'error'); return; }
    try {
        await api.post('/api/comments/', { movie_id: movieId, content });
        input.value = '';
        showToast('评论发表成功', 'success');
        loadMovieDetail(movieId);
    } catch (err) {
        showToast(err.response?.data?.detail || '评论发表失败', 'error');
    }
}

async function deleteComment(commentId) {
    if (!confirm('确定要删除这条评论吗？')) return;
    try {
        await api.delete(`/api/comments/${commentId}`);
        showToast('评论已删除', 'success');
        const movieId = STATE.currentMovieId;
        if (movieId) loadMovieDetail(movieId);
        if (STATE.currentPage === 'admin' && typeof loadAdminComments === 'function') loadAdminComments();
    } catch (err) {
        showToast(err.response?.data?.detail || '删除失败', 'error');
    }
}
