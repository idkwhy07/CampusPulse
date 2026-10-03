const CampusPulseAPI = (() => {
  const TOKEN_KEY = 'campuspulse_token';
  const USER_KEY = 'campuspulse_user';

  function getToken() {
    return localStorage.getItem(TOKEN_KEY) || '';
  }

  function getUser() {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch (_) {
      return null;
    }
  }

  function saveSession(data) {
    localStorage.setItem(TOKEN_KEY, data.token);
    localStorage.setItem(USER_KEY, JSON.stringify(data.user));
  }

  function clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  function homeFor(user) {
    return user?.role === 'STAFF' ? '/admin' : '/';
  }

  function requireRole(expectedRole) {
    const token = getToken();
    const user = getUser();
    if (!token || !user) {
      window.location.replace('/login');
      return false;
    }
    if (expectedRole && user.role !== expectedRole) {
      window.location.replace(homeFor(user));
      return false;
    }
    return true;
  }

  async function login(email, password) {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await safeJSON(response);
    if (!response.ok) {
      throw new Error(data.error || 'Đăng nhập thất bại.');
    }
    saveSession(data);
    return data;
  }

  async function register(name, email, password) {
    const response = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    });
    const data = await safeJSON(response);
    if (!response.ok) {
      if (response.status === 409) throw new Error('Email này đã được đăng ký.');
      throw new Error(data.error || 'Đăng ký thất bại.');
    }
    saveSession(data);
    return data;
  }

  function logout() {
    clearSession();
    window.location.replace('/login');
  }

  async function safeJSON(response) {
    try {
      return await response.json();
    } catch (_) {
      return {};
    }
  }

  async function apiFetch(url, options = {}, expectedRole = null) {
    if (!requireRole(expectedRole)) {
      throw new Error('Unauthenticated');
    }

    const headers = new Headers(options.headers || {});
    headers.set('Authorization', `Bearer ${getToken()}`);
    const response = await fetch(url, { ...options, headers });

    if (response.status === 401) {
      clearSession();
      window.location.replace('/login');
      throw new Error('Phiên đăng nhập đã hết hạn.');
    }
    if (response.status === 403) {
      const user = getUser();
      window.location.replace(homeFor(user));
      throw new Error('Bạn không có quyền thực hiện thao tác này.');
    }
    return response;
  }

  return {
    apiFetch,
    clearSession,
    getToken,
    getUser,
    homeFor,
    login,
    logout,
    register,
    requireRole,
  };
})();


document.addEventListener('click', (event) => {
  const button = event.target.closest('[data-logout]');
  if (!button) return;
  CampusPulseAPI.logout();
});
