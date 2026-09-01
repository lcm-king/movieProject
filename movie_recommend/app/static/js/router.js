// ========== Global State ==========
const STATE = {
    user: null,
    currentPage: 'home',
    currentMovieId: null,
    moviePage: 1,
    movieFilters: {},
    adminTab: 'users',
};

// ========== Navigation ==========
function navigateTo(page, params) {
    STATE.currentPage = page;
    document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
    const pageEl = document.getElementById(`page-${page}`);
    if (pageEl) pageEl.style.display = 'block';

    // Restore original HTML if previously cached by auth guard
    if (pageEl && pageEl.dataset.originalHtml) {
        pageEl.innerHTML = pageEl.dataset.originalHtml;
        delete pageEl.dataset.originalHtml;
    }

    document.querySelectorAll('.nav-links a').forEach(a => {
        a.classList.toggle('active', a.getAttribute('href') === `#${page}`);
    });

    const searchBox = document.getElementById('navSearchBox');
    if (searchBox) {
        searchBox.style.display = (page === 'movies' || page === 'home') ? 'flex' : 'none';
    }

    // Auth check: pages that require login
    if (['recommendations', 'ai', 'profile'].includes(page) && !STATE.user) {
        // Cache original HTML before replacing so it can be restored after login
        if (pageEl && !pageEl.dataset.originalHtml) {
            pageEl.dataset.originalHtml = pageEl.innerHTML;
        }
        pageEl.innerHTML =
            `<div style="text-align:center;padding:80px 24px;">
                <p style="font-size:1.2rem;margin-bottom:16px;color:var(--text-secondary);">请先登录以访问此页面</p>
                <button class="btn-hero" onclick="showAuthModal('login')">立即登录</button>
                <button class="btn-login" style="margin-left:12px;padding:14px 32px;" onclick="navigateTo('home')">返回首页</button>
            </div>`;
        window.scrollTo({ top: 0, behavior: 'smooth' });
        return;
    }

    // Admin page: only admin users
    if (page === 'admin') {
        if (!STATE.user) {
            if (pageEl && !pageEl.dataset.originalHtml) {
                pageEl.dataset.originalHtml = pageEl.innerHTML;
            }
            pageEl.innerHTML =
                `<div style="text-align:center;padding:80px 24px;">
                    <p style="font-size:1.2rem;margin-bottom:16px;color:var(--text-secondary);">请先登录以访问此页面</p>
                    <button class="btn-hero" onclick="showAuthModal('login')">立即登录</button>
                    <button class="btn-login" style="margin-left:12px;padding:14px 32px;" onclick="navigateTo('home')">返回首页</button>
                </div>`;
            window.scrollTo({ top: 0, behavior: 'smooth' });
            return;
        }
        if (STATE.user.role !== 'admin') {
            pageEl.innerHTML =
                `<div style="text-align:center;padding:80px 24px;">
                    <p style="font-size:1.2rem;margin-bottom:16px;color:var(--danger);">⚠️ 仅管理员可访问</p>
                    <button class="btn-hero" onclick="navigateTo('home')">返回首页</button>
                </div>`;
            window.scrollTo({ top: 0, behavior: 'smooth' });
            return;
        }
    }

    switch (page) {
        case 'home': loadHomePage(); break;
        case 'movies':
            if (!params?.keepFilters) {
                STATE.movieFilters = {};
                STATE.moviePage = 1;
                document.querySelectorAll('.filter-genre-chip').forEach(b => b.classList.remove('selected'));
                ['filterRatingMin','filterRatingMax','filterYearFrom','filterYearTo','navSearchInput'].forEach(id => {
                    const el = document.getElementById(id);
                    if (el) el.value = '';
                });
            }
            loadMoviesPage(); break;
        case 'movie-detail': loadMovieDetail(params); break;
        case 'recommendations': loadRecommendations(); break;
        case 'ai': loadAIPage(); break;
        case 'profile': loadProfilePage(); break;
        case 'admin': loadAdminPage(); break;
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function performSearch() {
    const query = document.getElementById('navSearchInput').value.trim();
    if (!query) return;
    STATE.movieFilters = { search: query };
    STATE.moviePage = 1;
    // Clear DOM filter state so nav search is a fresh start
    document.querySelectorAll('.filter-genre-chip').forEach(b => b.classList.remove('selected'));
    ['filterRatingMin','filterRatingMax','filterYearFrom','filterYearTo'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    navigateTo('movies', { keepFilters: true });
}

function loadUserFromStorage() {
    const token = localStorage.getItem('token');
    const userStr = localStorage.getItem('user');
    if (token && userStr) {
        try {
            STATE.user = JSON.parse(userStr);
            updateNavUI();
        } catch (e) {
            localStorage.clear();
        }
    }
}

// Helper: jump to AI chat with a movie question pre-filled
function navigateToAIMovieQA(movieId, movieTitle) {
    navigateTo('ai');
    const input = document.getElementById('chatInput');
    if (input) {
        input.value = `告诉我关于《${movieTitle}》的信息`;
        // Wait a beat then auto-send
        setTimeout(() => sendChatMessage(), 500);
    }
}
