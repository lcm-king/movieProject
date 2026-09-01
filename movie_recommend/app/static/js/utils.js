// ========== Shared Constants & Utilities ==========
const ALL_GENRES = ['动作', '喜剧', '剧情', '科幻', '爱情', '犯罪', '悬疑', '动画', '奇幻', '冒险', '战争', '历史', '音乐', '灾难', '家庭', '恐怖'];

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function showToast(message, type) {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function renderMovieCard(movie) {
    const coverUrl = movie.cover_url || `https://picsum.photos/seed/${movie.id}/400/600`;
    const year = movie.release_year || '未知';
    return `
        <div class="movie-card" onclick="navigateTo('movie-detail', ${movie.id})">
            <img class="movie-card-cover" src="${coverUrl}" alt="${escapeHtml(movie.title)}" loading="lazy">
            <div class="movie-card-info">
                <div class="movie-card-title">${escapeHtml(movie.title)}</div>
                <div class="movie-card-genre">${escapeHtml(movie.genre)} · ${year}</div>
                <div class="movie-card-rating">⭐ ${movie.avg_rating.toFixed(1)} (${movie.rating_count}评)</div>
            </div>
        </div>`;
}
