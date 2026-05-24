/* ============================================================================
   Noir Medical — Shared Utilities (with Auth)
   ============================================================================ */

/* ── API Base URL ─────────────────────────────────────────────────────────── */
// 使用相对路径 - 自动适配所有环境（本地/公网/cpolar等）
// 原理：当用户访问 https://xxx.cpolar.top/static/index.html 时
//       相对路径 /api/xxx 会自动解析为 https://xxx.cpolar.top/api/xxx
const API_BASE = '';

console.log('[API_BASE] 使用相对路径模式（自动适配所有环境）');
console.log('[API_BASE] 当前页面:', window.location.href);

/* ── Session ─────────────────────────────────────────────────────────────── */
function getSessionId() {
  var id = localStorage.getItem('sessionId');
  if (!id) {
    id = 's_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
    localStorage.setItem('sessionId', id);
  }
  return id;
}

/* ── Auth helpers ────────────────────────────────────────────────────────── */
function getToken() {
  return localStorage.getItem('token') || '';
}

function setToken(t) {
  localStorage.setItem('token', t);
}

function clearToken() {
  localStorage.removeItem('token');
}

function isLoggedIn() {
  return !!localStorage.getItem('token');
}

function getUserName() {
  return localStorage.getItem('username') || '';
}

function setUserName(n) {
  if (n) localStorage.setItem('username', n);
  else localStorage.removeItem('username');
}

function logout() {
  clearToken();
  setUserName('');
  updateAuthUI();
}

/* ── Theme ───────────────────────────────────────────────────────────────── */
function getTheme() {
  return localStorage.getItem('theme') || 'dark';
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
  var icon = document.getElementById('themeIcon');
  if (icon) {
    icon.className = theme === 'dark' ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
  }
}

function toggleTheme() {
  var current = document.documentElement.getAttribute('data-theme') || 'dark';
  var next = current === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  return next;
}

function initTheme() {
  applyTheme(getTheme());
}

/* ── Auth UI ─────────────────────────────────────────────────────────────── */
function updateAuthUI() {
  var authBtn = document.getElementById('authBtn');
  var authText = document.getElementById('authText');
  var overlay = document.getElementById('profileAuthOverlay');
  var loggedIn = isLoggedIn();
  var name = getUserName();

  if (loggedIn && name) {
    if (authText) authText.textContent = name;
    if (authBtn) {
      authBtn.innerHTML = '<i class="fa-solid fa-right-from-bracket"></i>';
      authBtn.title = '退出登录';
      authBtn.onclick = function() { logout(); };
    }
    if (overlay) overlay.style.display = 'none';
  } else {
    if (authText) authText.textContent = '游客';
    if (authBtn) {
      authBtn.innerHTML = '<i class="fa-solid fa-arrow-right-to-bracket"></i>';
      authBtn.title = '去登录';
      authBtn.onclick = function() { window.location.href = '/static/login.html'; };
    }
    // Show subtle guest notice instead of blocking overlay
    if (overlay) overlay.style.display = 'flex';
  }
}

/* ── HTML escaping ───────────────────────────────────────────────────────── */
function escapeHtml(str) {
  if (!str) return '';
  var div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/* ── API helpers (auto-carry token) ──────────────────────────────────────── */
async function apiGet(url) {
  var headers = {};
  var token = getToken();
  if (token) headers['Authorization'] = 'Bearer ' + token;
  var fullUrl = API_BASE + url;

  console.log('[apiGet] 请求URL:', fullUrl);
  console.log('[apiGet] Token状态:', token ? '已附加' : '无Token');

  var r = await fetch(fullUrl, { headers: headers });
  console.log('[apiGet] 响应状态:', r.status, r.ok ? '✓ 成功' : '✗ 失败');

  if (!r.ok) throw new Error('HTTP ' + r.status);
  return r.json();
}

async function apiPost(url, data) {
  var headers = { 'Content-Type': 'application/json' };
  var token = getToken();
  if (token) headers['Authorization'] = 'Bearer ' + token;
  var fullUrl = API_BASE + url;

  console.log('[apiPost] 请求URL:', fullUrl);
  console.log('[apiPost] Token状态:', token ? '已附加' : '无Token');
  console.log('[apiPost] 请求数据:', data ? JSON.stringify(data).substring(0, 100) : '空');

  var r = await fetch(fullUrl, {
    method: 'POST',
    headers: headers,
    body: JSON.stringify(data),
  });

  console.log('[apiPost] 响应状态:', r.status, r.ok ? '✓ 成功' : '✗ 失败');

  if (!r.ok) {
    var err = await r.json().catch(function () { return {}; });
    console.error('[apiPost] 错误详情:', err);
    throw new Error(err.detail || 'HTTP ' + r.status);
  }
  return r.json();
}

/* ── DOM helpers ─────────────────────────────────────────────────────────── */
function $(sel, parent) { return (parent || document).querySelector(sel); }
function $$(sel, parent) { return (parent || document).querySelectorAll(sel); }

/* ── Debounce ────────────────────────────────────────────────────────────── */
function debounce(fn, delay) {
  var timer;
  return function () {
    var args = arguments;
    var self = this;
    clearTimeout(timer);
    timer = setTimeout(function () { fn.apply(self, args); }, delay);
  };
}

/* ── Init ────────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function () {
  initTheme();

  var token = getToken();
  if (token) {
    // Verify token is still valid
    fetch(API_BASE + '/api/auth/me', {
      headers: { 'Authorization': 'Bearer ' + token },
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.user) {
          setUserName(data.user.username);
        } else {
          clearToken();
          setUserName('');
        }
        updateAuthUI();
      })
      .catch(function () {
        // Network error — keep token, try to show username from localStorage
        updateAuthUI();
      });
  } else {
    updateAuthUI();
  }
});

// ==========================================
// 移动端交互 — 医疗AI智能客服
// ==========================================

(function() {
    const isMobile = window.innerWidth <= 768 || /Android|iPhone|iPad/i.test(navigator.userAgent);

    if (!isMobile) return;

    // 1. 创建汉堡菜单按钮
    function createMobileMenuBtn() {
        const topbar = document.querySelector('.topbar');
        if (!topbar || topbar.querySelector('.mobile-menu-btn')) return;

        const btn = document.createElement('button');
        btn.className = 'mobile-menu-btn';
        btn.innerHTML = '<i class="fas fa-bars"></i>';
        btn.style.cssText = `
            display: flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            background: none;
            border: none;
            color: var(--text-primary);
            font-size: 20px;
            cursor: pointer;
            margin-right: 8px;
        `;

        btn.addEventListener('click', toggleSidebar);
        topbar.insertBefore(btn, topbar.firstChild);
    }

    // 2. 创建遮罩层
    function createOverlay() {
        if (document.querySelector('.sidebar-overlay')) return;

        const overlay = document.createElement('div');
        overlay.className = 'sidebar-overlay';
        overlay.addEventListener('click', closeSidebar);
        document.body.appendChild(overlay);
    }

    // 3. 切换侧边栏
    function toggleSidebar() {
        const sidebar = document.querySelector('.session-sidebar');
        const overlay = document.querySelector('.sidebar-overlay');

        if (sidebar.classList.contains('open')) {
            closeSidebar();
        } else {
            sidebar.classList.add('open');
            overlay.classList.add('open');
            document.body.style.overflow = 'hidden';
        }
    }

    function closeSidebar() {
        const sidebar = document.querySelector('.session-sidebar');
        const overlay = document.querySelector('.sidebar-overlay');

        sidebar.classList.remove('open');
        overlay.classList.remove('open');
        document.body.style.overflow = '';
    }

    // 4. 监听窗口大小变化
    let lastWidth = window.innerWidth;
    window.addEventListener('resize', () => {
        const currentWidth = window.innerWidth;
        if (lastWidth <= 768 && currentWidth > 768) {
            // 从小屏切到大屏，关闭侧边栏
            closeSidebar();
        }
        lastWidth = currentWidth;
    });

    // 5. 触摸滑动关闭侧边栏
    let touchStartX = 0;
    document.addEventListener('touchstart', (e) => {
        touchStartX = e.touches[0].clientX;
    });

    document.addEventListener('touchend', (e) => {
        const touchEndX = e.changedTouches[0].clientX;
        const diff = touchStartX - touchEndX;

        // 从左向右滑动超过 50px，关闭侧边栏
        if (diff < -50 && document.querySelector('.session-sidebar.open')) {
            closeSidebar();
        }
    });

    // 6. 防止输入框被键盘遮挡
    const inputs = document.querySelectorAll('input, textarea');
    inputs.forEach(input => {
        input.addEventListener('focus', () => {
            setTimeout(() => {
                input.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 300);
        });
    });

    // 7. 初始化
    document.addEventListener('DOMContentLoaded', () => {
        createMobileMenuBtn();
        createOverlay();
    });

})();

// ==========================================
// PWA Service Worker 注册
// ==========================================

if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then((registration) => {
                console.log('SW 注册成功:', registration.scope);
            })
            .catch((error) => {
                console.log('SW 注册失败:', error);
            });
    });
}

// 检测是否已安装 PWA
window.addEventListener('appinstalled', () => {
    console.log('PWA 已安装到主屏幕');
});
