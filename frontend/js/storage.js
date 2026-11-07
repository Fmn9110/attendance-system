// 离线暂存与恢复：保存当前未同步的操作队列
const OfflineQueue = (() => {
  const KEY = 'att_pending_ops';

  function load() {
    try { return JSON.parse(localStorage.getItem(KEY) || '[]'); }
    catch (e) { return []; }
  }
  function save(queue) {
    localStorage.setItem(KEY, JSON.stringify(queue));
  }
  function push(op) {
    const q = load();
    q.push(Object.assign({ t: Date.now() }, op));
    save(q);
    render();
  }
  function clear() { save([]); render(); }
  function all() { return load(); }

  function render() {
    const bar = document.querySelector('.offline-bar');
    if (!bar) return;
    const n = load().length;
    if (n > 0) bar.textContent = `网络异常，${n} 条数据待同步`;
    bar.classList.toggle('show', n > 0);
  }

  // 网络恢复后自动重试队列
  async function flush(sender) {
    const q = load();
    if (!q.length) return;
    const remaining = [];
    for (const op of q) {
      try { await sender(op); }
      catch (e) { remaining.push(op); }
    }
    save(remaining);
    render();
  }

  window.addEventListener('online', () => flush(window.__offlineSender || (async () => {})));
  return { push, clear, all, flush, render };
})();
