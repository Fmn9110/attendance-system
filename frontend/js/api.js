// 统一 API 封装：Token、错误处理、离线队列
const API = (() => {
  const BASE = '';
  const TOKEN_KEY = 'att_token';
  const CLASS_KEY = 'att_class';

  function getToken() { return localStorage.getItem(TOKEN_KEY); }
  function setToken(token, cls) {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    if (cls) localStorage.setItem(CLASS_KEY, JSON.stringify(cls));
  }
  function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(CLASS_KEY);
  }
  function getClass() {
    try { return JSON.parse(localStorage.getItem(CLASS_KEY) || 'null'); }
    catch (e) { return null; }
  }

  async function request(path, options = {}) {
    const headers = Object.assign({ 'Content-Type': 'application/json' }, options.headers || {});
    const token = getToken();
    if (token) headers['Authorization'] = 'Bearer ' + token;
    const resp = await fetch(BASE + path, Object.assign({}, options, { headers }));
    let data;
    try { data = await resp.json(); }
    catch (e) { throw new Error('服务器响应异常'); }
    if (resp.status === 401) {
      // 登录页的 401 是密码错误，不跳转，让登录页自己显示错误
      const onLoginPage = location.pathname.endsWith('login.html');
      if (!onLoginPage) {
        clearToken();
        location.href = '/index.html';
      }
      throw new Error(data.message || data.detail || '未登录');
    }
    if (resp.status === 403) throw new Error(data.detail || data.message || '无权访问');
    if (!resp.ok) throw new Error(data.detail || data.message || ('HTTP ' + resp.status));
    return data;
  }

  return {
    getToken, setToken, clearToken, getClass,
    get: (p) => request(p, { method: 'GET' }),
    post: (p, body) => request(p, { method: 'POST', body: JSON.stringify(body || {}) }),
    postRaw: (p, body) => request(p, { method: 'POST', body: body }),
  };
})();
