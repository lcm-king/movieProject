// ========== API Configuration ==========
const API_BASE = '';
const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use(config => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

api.interceptors.response.use(
    res => res,
    err => {
        // Only trigger logout on 401 if user was actually logged in
        if (err.response?.status === 401 && localStorage.getItem('token')) {
            logout();
            showToast('登录已过期，请重新登录', 'error');
        } else if (err.response?.status === 403) {
            showToast('权限不足', 'error');
        }
        return Promise.reject(err);
    }
);
