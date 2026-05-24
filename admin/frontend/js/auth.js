/* ═══════════════════════════════════════════════════════════════════════════
   Admin — Auth & API Utilities
   ═══════════════════════════════════════════════════════════════════════════ */

function adminApi(url, method, data) {
  var headers = { 'Content-Type': 'application/json' };
  var token = localStorage.getItem('admin_token');
  if (token) headers['Authorization'] = 'Bearer ' + token;
  var opts = { method: method, headers: headers };
  if (data) opts.body = JSON.stringify(data);
  return fetch('/admin/api' + url, opts).then(function (r) {
    return r.json().then(function (json) {
      if (!r.ok || json.code !== 200) throw new Error(json.detail || 'Request failed');
      return json.data;
    });
  });
}

function handleLogin(e) {
  e.preventDefault();
  var btn = document.getElementById('loginBtn');
  var err = document.getElementById('loginError');
  btn.disabled = true; err.style.display = 'none';

  adminApi('/login', 'POST', {
    username: document.getElementById('loginUser').value.trim(),
    password: document.getElementById('loginPass').value
  }).then(function (data) {
    localStorage.setItem('admin_token', data.token);
    localStorage.setItem('admin_username', data.username);
    document.getElementById('loginOverlay').style.display = 'none';
    document.getElementById('adminApp').style.display = '';
    document.getElementById('adminName').textContent = data.username;
    loadDashboard();
    startAutoRefresh();
  }).catch(function (ex) {
    err.textContent = ex.message || '登录失败';
    err.style.display = 'block';
    btn.disabled = false;
  });
  return false;
}

function doLogout() {
  localStorage.removeItem('admin_token');
  localStorage.removeItem('admin_username');
  location.reload();
}

function switchAdminPanel(name) {
  document.querySelectorAll('.panel').forEach(function (p) { p.classList.remove('active'); });
  document.querySelectorAll('.nav-item').forEach(function (n) { n.classList.remove('active'); });
  var panel = document.getElementById('panel-' + name);
  if (panel) panel.classList.add('active');
  var nav = document.querySelector('[data-panel="' + name + '"]');
  if (nav) nav.classList.add('active');

  var loaders = {
    dashboard: loadDashboard,
    sessions: loadSessions,
    compliance: loadCompliance,
    qos: loadQos,
    system: loadSystem,
  };
  if (loaders[name]) loaders[name]();
}

var _autoRefreshTimer = null;
function startAutoRefresh() {
  if (_autoRefreshTimer) clearInterval(_autoRefreshTimer);
  _autoRefreshTimer = setInterval(function () {
    var active = document.querySelector('.panel.active');
    if (!active) return;
    var name = active.id.replace('panel-', '');
    var loaders = { dashboard: loadDashboard, sessions: loadSessions, compliance: loadCompliance, qos: loadQos, system: loadSystem };
    if (loaders[name]) loaders[name]();
  }, 30000);
}

function escapeHtml(str) {
  if (!str) return '';
  var d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
