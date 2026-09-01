// ========== Application Initialization ==========
document.addEventListener('DOMContentLoaded', () => {
    loadUserFromStorage();
    initGenreFilters();
    navigateTo('home');
});
