/* ═══════════════════════════════════════════════════════════════════════════
   Noir Medical — Chat Logic (with Session Sidebar)
   ═══════════════════════════════════════════════════════════════════════════ */

var sessionId = getSessionId();
var currentPanel = 'chat';

/* ── Context Memory System ──────────────────────────────────────────────── */
var chatContext = {};  // { sessionId: [ {role, content}, ... ] }
var MAX_CONTEXT_MSGS = 10;  // 保留最近10条消息作为上下文

function saveCurrentContext() {
  if (sessionId && chatContext[sessionId]) {
    localStorage.setItem('ctx_' + sessionId, JSON.stringify(chatContext[sessionId]));
  }
}

function loadContextFromStorage(sid) {
  try {
    var stored = localStorage.getItem('ctx_' + sid);
    if (stored) {
      chatContext[sid] = JSON.parse(stored);
      return true;
    }
  } catch(e) {}
  return false;
}

function addToContext(sid, role, content) {
  if (!chatContext[sid]) chatContext[sid] = [];
  chatContext[sid].push({ role: role, content: content });
  // 只保留最近 N 条消息（用户+AI 各算一条）
  if (chatContext[sid].length > MAX_CONTEXT_MSGS * 2) {
    chatContext[sid] = chatContext[sid].slice(-MAX_CONTEXT_MSGS * 2);
  }
}

function getContextMessages(sid) {
  sid = sid || sessionId;
  if (!chatContext[sid]) return [];
  return chatContext[sid];
}

/* ── Session Management ─────────────────────────────────────────────────── */
async function loadSessionList(retryCount) {
  retryCount = retryCount || 0;
  var emptyEl = document.getElementById('sessionEmpty');
  var emptyText = document.getElementById('sessionEmptyText');
  var list = document.getElementById('sessionList');

  // Clear old session items (but keep #sessionEmpty)
  list.querySelectorAll('.session-item').forEach(function (el) { el.remove(); });

  var token = getToken();
  console.log('[loadSessionList] 尝试 #' + (retryCount + 1) + ', token:', token ? '已获取 (' + token.substring(0, 20) + '...)' : '未获取');

  if (!isLoggedIn()) {
    // 如果是首次加载且未登录，等待100ms后重试（最多5次，总计500ms）
    // 这解决了从登录页跳转过来时token还未读取的问题
    if (retryCount < 5) {
      console.log('[loadSessionList] 等待token就绪，100ms后重试...');
      setTimeout(function() {
        loadSessionList(retryCount + 1);
      }, 100);
      return;
    }
    console.warn('[loadSessionList] 重试5次后仍未检测到登录状态');
    emptyEl.style.display = 'block';
    emptyText.textContent = '登录后查看历史会话';
    return;
  }

  console.log('[loadSessionList] 已检测到登录状态，开始加载会话列表...');
  try {
    var data = await apiGet('/api/session/list');
    console.log('[loadSessionList] 获取到会话数据:', data.sessions ? data.sessions.length : 0, '条');
    if (!data.sessions || data.sessions.length === 0) {
      emptyEl.style.display = 'block';
      emptyText.textContent = '暂无会话，点击上方按钮新建';
      return;
    }
    emptyEl.style.display = 'none';

    data.sessions.forEach(function (s) {
      var title = s.title || '新会话';
      var time = formatTime(s.last_active);
      var activeClass = s.session_id === sessionId ? ' active' : '';
      var div = document.createElement('div');
      div.className = 'session-item' + activeClass;
      div.id = 'item-' + s.session_id;
      div.onclick = function() { switchSession(s.session_id); };
      div.innerHTML =
        '<div class="session-item-title">' + escapeHtml(title) + '</div>' +
        '<div class="session-item-meta">' +
          '<span>' + (s.msg_count || 0) + ' 条消息</span>' +
          '<span>' + time + '</span>' +
        '</div>' +
        '<div class="session-item-actions">' +
          '<button class="session-action-btn" onclick="event.stopPropagation();renameSession(\'' + s.session_id + '\')" title="重命名"><i class="fa-solid fa-pen"></i></button>' +
          '<button class="session-action-btn" onclick="event.stopPropagation();deleteCurrentSession(\'' + s.session_id + '\')" title="删除"><i class="fa-solid fa-trash"></i></button>' +
        '</div>';
      list.appendChild(div);
    });
  } catch (e) {
    /* sidebar unavailable */
  }
}

function formatTime(dateStr) {
  if (!dateStr) return '';
  var d = new Date(dateStr);
  var now = new Date();
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  }
  var yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  if (d.toDateString() === yesterday.toDateString()) {
    return '昨天';
  }
  return (d.getMonth() + 1) + '/' + d.getDate();
}

async function createNewSession() {
  console.log('[createNewSession] 开始创建新会话...');
  console.log('[createNewSession] 当前sessionId:', sessionId);
  console.log('[createNewSession] 登录状态:', isLoggedIn() ? '已登录' : '未登录');
  console.log('[createNewSession] Token:', getToken() ? '存在 (' + getToken().substring(0, 20) + '...)' : '不存在');
  console.log('[createNewSession] API_BASE:', typeof API_BASE !== 'undefined' ? API_BASE : '未定义');

  // Save current context before creating new session
  saveCurrentContext();

  try {
    console.log('[createNewSession] 调用API: /api/session/create');
    var data = await apiPost('/api/session/create', {});
    console.log('[createNewSession] API调用成功，返回数据:', data);

    if (data && data.session_id) {
      sessionId = data.session_id;
      localStorage.setItem('sessionId', data.session_id);
      console.log('[createNewSession] 新会话ID已保存:', sessionId);
    } else {
      throw new Error('服务器未返回session_id');
    }

    // Initialize empty context for new session
    chatContext[sessionId] = [];

    // 刷新会话列表（不重新检测登录状态）
    loadSessionList();
    clearChatToWelcome();

    console.log('[createNewSession] 新会话创建完成！');
  } catch (e) {
    console.error('[createNewSession] API调用失败:', e.message, e.stack);
    console.warn('[createNewSession] 降级为本地会话模式');

    // 降级：使用本地生成的会话ID（不影响登录状态）
    var newId = 's_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
    
    // 只更新sessionId，不清除其他状态
    localStorage.setItem('sessionId', newId);
    sessionId = newId;
    chatContext[sessionId] = [];
    
    clearChatToWelcome();
    console.log('[createNewSession] 本地会话已创建:', newId);
  }
  
  // 验证登录状态是否保持
  console.log('[createNewSession] 操作后登录状态:', isLoggedIn() ? '已登录' : '未登录');
}

function clearChatToWelcome() {
  var msgs = document.getElementById('chatMessages');
  msgs.innerHTML = '<div class="msg-row ai"><div class="msg-avatar"><i class="fa-solid fa-staff-snake"></i></div><div class="msg-bubble">您好！我是您的医疗健康助手。<br>请问有什么可以帮助您的？</div></div>';
}

function switchSession(newId) {
  // Save current session context before switching
  saveCurrentContext();
  
  sessionId = newId;
  localStorage.setItem('sessionId', newId);
  
  // Try to load context from local storage first
  var hasLocalCtx = loadContextFromStorage(newId);
  
  clearChatToWelcome();
  
  // Highlight active
  document.querySelectorAll('.session-item').forEach(function (el) {
    el.classList.remove('active');
  });
  var item = document.getElementById('item-' + newId);
  if (item) item.classList.add('active');
  
  // Load history and merge with context
  loadChatHistory(newId, hasLocalCtx);
}

async function loadChatHistory(sid, hasLocalCtx) {
  sid = sid || sessionId;
  var msgs = document.getElementById('chatMessages');
  
  // Show loading indicator for large histories
  msgs.innerHTML = '<div class="loading-hint"><i class="fa-solid fa-spinner fa-spin"></i> 加载对话记录...</div>';
  
  // Use requestIdleCallback or setTimeout to avoid blocking
  await new Promise(function(resolve) { setTimeout(resolve, 10); });
  
  try {
    var data = await apiGet('/api/chat/history/' + sid);
    if (data.history && data.history.length > 0) {
      // Reset context for this session
      chatContext[sid] = [];
      
      // Build all messages first, then render in batch
      var items = [];
      data.history.forEach(function (h) {
        items.push({ role: 'user', content: h.user_message });
        addToContext(sid, 'user', h.user_message);
        if (h.ai_response) {
          items.push({ role: 'assistant', content: h.ai_response, skipContext: true });
          addToContext(sid, 'assistant', h.ai_response);
        }
      });
      
      // Batch render with DocumentFragment for performance
      batchRenderMessages(items, sid);
      
      // Save to local storage
      saveCurrentContext();
    } else if (!hasLocalCtx) {
      clearChatToWelcome();
    } else {
      renderFromContext(sid);
    }
  } catch (e) {
    if (hasLocalCtx) {
      renderFromContext(sid);
    } else {
      clearChatToWelcome();
    }
  }
}

/* ── Batch Render Messages (Performance Optimized) ───────────────────────── */
function batchRenderMessages(items, sid) {
  var msgs = document.getElementById('chatMessages');
  msgs.innerHTML = '';
  
  if (items.length === 0) return;
  
  // Use DocumentFragment to minimize reflows
  var fragment = document.createDocumentFragment();
  var now = Date.now();
  
  items.forEach(function(item, idx) {
    var row = document.createElement('div');
    row.className = 'msg-row ' + (item.role === 'user' ? 'user' : 'ai');
    
    var avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.innerHTML = item.role === 'user'
      ? '<i class="fa-solid fa-user"></i>'
      : '<i class="fa-solid fa-staff-snake"></i>';
    
    var bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    bubble.innerHTML = (item.content || '').replace(/\n/g, '<br>');
    
    var time = document.createElement('div');
    time.className = 'msg-time';
    time.textContent = new Date(now - (items.length - idx) * 60000).toLocaleTimeString('zh-CN', {
      hour: '2-digit', minute: '2-digit',
    });
    bubble.appendChild(time);
    
    row.append(avatar, bubble);
    fragment.appendChild(row);
  });
  
  // Single DOM operation
  msgs.appendChild(fragment);
  
  // Scroll to bottom after render
  requestAnimationFrame(function() {
    msgs.scrollTop = msgs.scrollHeight;
  });
}

function renderFromContext(sid) {
  var ctx = chatContext[sid];
  if (!ctx || ctx.length === 0) return;
  
  var items = ctx.map(function(msg) {
    return {
      role: msg.role,
      content: msg.content,
    };
  });
  
  batchRenderMessages(items, sid);
}

async function renameSession(sid) {
  var title = prompt('输入新标题：');
  if (!title) return;
  try {
    await apiPost('/api/session/' + sid + '/rename', { title: title });
    loadSessionList();
  } catch (e) {
    alert('重命名失败');
  }
}

async function deleteCurrentSession(sid) {
  if (!confirm('确定删除此会话？')) return;
  
  // Clear context for deleted session
  delete chatContext[sid];
  localStorage.removeItem('ctx_' + sid);
  localStorage.removeItem('lastActiveSession');
  
  try {
    var r = await fetch(API_BASE + '/api/session/' + sid, {
      method: 'DELETE',
      headers: isLoggedIn() ? { 'Authorization': 'Bearer ' + getToken() } : {},
    });
    if (r.ok) {
      if (sid === sessionId) {
        var newId = 's_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
        localStorage.setItem('sessionId', newId);
        sessionId = newId;
        chatContext[newId] = [];
        clearChatToWelcome();
      }
      loadSessionList();
    }
  } catch (e) {
    alert('删除失败');
  }
}

/* ── Panel switching ────────────────────────────────────────────────────── */
function switchPanel(name) {
  currentPanel = name;
  document.querySelectorAll('.panel').forEach(function (p) { p.classList.remove('active'); });
  document.querySelectorAll('.nav-tab').forEach(function (t) { t.classList.remove('active'); });

  var panel = document.getElementById(name + 'Panel');
  if (panel) panel.classList.add('active');

  var tab = document.querySelector('[data-tab="' + name + '"]');
  if (tab) tab.classList.add('active');

  if (name === 'profile') loadProfile();
}

/* ── Chat messaging ─────────────────────────────────────────────────────── */
function addMessage(content, isUser, type, emotion) {
  var msgs = document.getElementById('chatMessages');
  var row = document.createElement('div');
  row.className = 'msg-row ' + (isUser ? 'user' : 'ai');

  var avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  avatar.innerHTML = isUser
    ? '<i class="fa-solid fa-user"></i>'
    : '<i class="fa-solid fa-staff-snake"></i>';

  var bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.innerHTML = (content || '').replace(/\n/g, '<br>');

  var time = document.createElement('div');
  time.className = 'msg-time';
  time.textContent = new Date().toLocaleTimeString('zh-CN', {
    hour: '2-digit', minute: '2-digit',
  });
  bubble.appendChild(time);

  if (!isUser && (type || emotion)) {
    var tags = document.createElement('div');
    tags.className = 'msg-tags';
    if (type && type !== '其他') {
      var t = document.createElement('span');
      t.className = 'msg-tag tag-type'; t.textContent = type; tags.appendChild(t);
    }
    if (emotion && emotion !== '平静') {
      var e = document.createElement('span');
      e.className = 'msg-tag tag-emotion'; e.textContent = emotion; tags.appendChild(e);
    }
    bubble.appendChild(tags);
  }

  row.append(avatar, bubble);
  msgs.appendChild(row);
  msgs.scrollTop = msgs.scrollHeight;
  return row;
}

function addTyping() {
  var msgs = document.getElementById('chatMessages');
  var row = document.createElement('div');
  row.className = 'msg-row ai'; row.id = 'typingRow';
  row.innerHTML = '<div class="msg-avatar"><i class="fa-solid fa-staff-snake"></i></div>' +
    '<div class="msg-bubble typing-indicator"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></div>';
  msgs.appendChild(row);
  msgs.scrollTop = msgs.scrollHeight;
  return row;
}

function removeTyping() {
  var el = document.getElementById('typingRow');
  if (el) el.remove();
}

async function sendMsg() {
  var input = document.getElementById('msgInput');
  var msg = input.value.trim();
  if (!msg) return;

  input.value = '';
  var btn = document.getElementById('sendBtn');
  btn.disabled = true;
  addMessage(msg, true);
  
  // Add user message to context
  addToContext(sessionId, 'user', msg);
  
  var typing = addTyping();

  try {
    // Get recent context for the API call
    var context = getContextMessages(sessionId);
    
    var data = await apiPost('/api/chat/send_with_type', {
      session_id: sessionId,
      message: msg,
      context: context.slice(0, -1),  // Send all except current message (already in message field)
    });
    removeTyping();
    addMessage(data.response, false, data.question_type, data.emotion_type);
    
    // Add AI response to context
    addToContext(sessionId, 'assistant', data.response);
    
    // Save context to local storage
    saveCurrentContext();
    
    // Refresh sidebar if logged in
    if (isLoggedIn()) loadSessionList();
  } catch (e) {
    removeTyping();
    addMessage('网络异常，请稍后重试', false);
  } finally {
    btn.disabled = false;
    input.focus();
  }
}

function sendQuick(text) {
  document.getElementById('msgInput').value = text;
  switchPanel('chat');
  sendMsg();
}

function clearInput() {
  var input = document.getElementById('msgInput');
  input.value = '';
  input.focus();
}

/* ── Image upload ───────────────────────────────────────────────────────── */
async function handleChatImage(event) {
  var file = event.target.files[0];
  if (!file) return;

  addMessage('[图片]', true);
  var typing = addTyping();

  var formData = new FormData();
  formData.append('file', file);
  formData.append('session_id', sessionId);

  try {
    var r = await fetch(API_BASE + '/api/chat/send_image', { method: 'POST', body: formData });
    var d = await r.json();
    removeTyping();
    addMessage(d.response, false, d.question_type, d.emotion_type);
  } catch (e) {
    removeTyping();
    addMessage('图片发送失败', false);
  }
  event.target.value = '';
}

/* ── Voice input ────────────────────────────────────────────────────────── */
function startVoiceInput() {
  var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    alert('您的浏览器不支持语音输入，请使用Chrome浏览器');
    return;
  }
  var recognition = new SpeechRecognition();
  recognition.lang = 'zh-CN';
  recognition.interimResults = false;
  recognition.onresult = function (event) {
    document.getElementById('msgInput').value = event.results[0][0].transcript;
    sendMsg();
  };
  recognition.onerror = function (event) {
    alert('语音识别失败: ' + event.error);
  };
  switchPanel('chat');
  recognition.start();
}

/* ── Health Profile ────────────────────────────────────────────────────── */
function clearProfileForm() {
  document.getElementById('pfName').value = '';
  document.getElementById('pfGender').value = '';
  document.getElementById('pfAge').value = '';
  document.getElementById('pfHeight').value = '';
  document.getElementById('pfWeight').value = '';
  document.getElementById('pfAllergies').value = '';
  document.getElementById('pfDiseases').value = '';
  document.getElementById('pfMedications').value = '';
  document.getElementById('profileSummary').innerHTML = '<div class="empty-state"><i class="fa-solid fa-file-medical empty-icon"></i><p>尚未填写健康档案</p></div>';
}

async function loadProfile() {
  if (!isLoggedIn()) { clearProfileForm(); return; }
  try {
    var data = await apiGet('/api/health/profile/' + sessionId);
    if (!data.profile) { clearProfileForm(); return; }
    var p = data.profile;
    document.getElementById('pfName').value = p.name || '';
    document.getElementById('pfGender').value = p.gender || '';
    document.getElementById('pfAge').value = p.age || '';
    document.getElementById('pfHeight').value = p.height || '';
    document.getElementById('pfWeight').value = p.weight || '';
    document.getElementById('pfAllergies').value = p.allergies || '';
    document.getElementById('pfDiseases').value = p.diseases || '';
    document.getElementById('pfMedications').value = p.medications || '';
    var html = '<div class="profile-stat"><div class="stat-val">' + escapeHtml(p.name || '-') + '</div><div class="stat-lbl">姓名</div></div>' +
      '<div class="profile-stat"><div class="stat-val">' + escapeHtml(p.gender || '-') + '</div><div class="stat-lbl">性别</div></div>' +
      '<div class="profile-stat"><div class="stat-val">' + (p.age || '-') + '</div><div class="stat-lbl">年龄</div></div>';
    if (p.height && p.weight) {
      var bmi = (p.weight / ((p.height / 100) * (p.height / 100))).toFixed(1);
      html += '<div class="profile-stat"><div class="stat-val">' + bmi + '</div><div class="stat-lbl">体质指数</div></div>';
    }
    document.getElementById('profileSummary').innerHTML = html;
  } catch (e) { clearProfileForm(); }
}

async function saveProfile() {
  var payload = {
    session_id: sessionId,
    name: document.getElementById('pfName').value,
    gender: document.getElementById('pfGender').value,
    age: parseInt(document.getElementById('pfAge').value) || null,
    height: parseFloat(document.getElementById('pfHeight').value) || null,
    weight: parseFloat(document.getElementById('pfWeight').value) || null,
    allergies: document.getElementById('pfAllergies').value,
    diseases: document.getElementById('pfDiseases').value,
    medications: document.getElementById('pfMedications').value,
  };
  try {
    await apiPost('/api/health/profile/save', payload);
    alert(isLoggedIn() ? '健康档案已保存' : '档案已保存（游客模式仅当前会话有效）');
    loadProfile();
  } catch (e) {
    alert('保存失败: ' + (e.message || '未知错误'));
  }
}

async function runHealthAssess() {
  try {
    var data = await apiPost('/api/health/assess', { session_id: sessionId });
    var card = document.getElementById('assessCard');
    card.style.display = 'block';
    document.getElementById('assessResult').textContent = data.assessment;
    card.scrollIntoView({ behavior: 'smooth' });
  } catch (e) { alert('评估失败'); }
}

/* ── Modal-based services ───────────────────────────────────────────────── */
function openModal(title, bodyHtml, actionFn) {
  document.getElementById('modalTitle').textContent = title;
  document.getElementById('modalBody').innerHTML = bodyHtml;
  var resp = document.getElementById('modalResponse');
  resp.style.display = 'none';
  resp.textContent = '';
  document.getElementById('genericModal').classList.add('show');
  window._modalAction = actionFn;
}

function closeModal() {
  document.getElementById('genericModal').classList.remove('show');
}

function showModalResponse(text) {
  var resp = document.getElementById('modalResponse');
  resp.style.display = 'block';
  resp.textContent = text;
}

async function executeModalService(endpoint, extraFields) {
  var q = document.getElementById('modalInput').value.trim();
  if (!q) return;
  showModalResponse('查询中...');
  try {
    var data = await apiPost(endpoint, Object.assign({ session_id: sessionId, query: q }, extraFields || {}));
    showModalResponse(data.response);
  } catch (e) { showModalResponse('查询失败，请稍后重试'); }
}

function openTcmModal() {
  openModal('中医科普咨询',
    '<p style="font-size:13px;color:var(--text-secondary);margin-bottom:12px">输入您想了解的中医药知识，获取传统文化科普（不提供诊疗建议）</p>' +
    '<input class="form-input" id="modalInput" placeholder="如：中医的阴阳学说是什么？">' +
    '<button class="btn btn-primary mt-md" style="width:100%" onclick="executeModalService(\'/api/health/tcm\')">查询</button>');
}

function openMedicationModal() {
  openModal('药品信息查询',
    '<p style="font-size:13px;color:var(--text-secondary);margin-bottom:12px">输入药品名称或拍照识别药品包装/说明书/药片</p>' +
    '<div style="display:flex;gap:8px;margin-bottom:12px">' +
    '<input class="form-input" id="modalInput" placeholder="输入药品通用名称..." style="flex:1">' +
    '<button class="btn btn-primary" style="white-space:nowrap" onclick="executeModalService(\'/api/health/medication\')"><i class="fa-solid fa-search"></i> 查询</button>' +
    '</div>' +
    '<div style="text-align:center;color:var(--text-muted);font-size:12px;margin:8px 0">或</div>' +
    '<input type="file" id="medFileInput" accept="image/*" capture="environment" style="display:none" onchange="execMedicationImage(event)">' +
    '<button class="btn btn-outline" style="width:100%" onclick="document.getElementById(\'medFileInput\').click()"><i class="fa-solid fa-camera"></i> 拍照识别药品包装/说明书/药片</button>');
}

async function execMedicationImage(event) {
  var file = event.target.files[0];
  if (!file) return;
  showModalResponse('正在识别药品...');
  var fd = new FormData();
  fd.append('file', file);
  fd.append('session_id', sessionId);
  try {
    var r = await fetch(API_BASE + '/api/health/medication_image', { method: 'POST', body: fd });
    var d = await r.json();
    showModalResponse(d.response);
  } catch (e) { showModalResponse('识别失败，请确保图片清晰后重试'); }
  event.target.value = '';
}

function openHospitalModal() {
  openModal('找医院/科室',
    '<p style="font-size:13px;color:var(--text-secondary);margin-bottom:12px">输入您想查询的医院科室信息，获取就医指引</p>' +
    '<input class="form-input" id="modalInput" placeholder="如：北京三甲医院有哪些科室？">' +
    '<button class="btn btn-primary mt-md" style="width:100%" onclick="executeModalService(\'/api/health/hospital\')">查询</button>');
}

function openLifestyleModal(category) {
  var titles = { '饮食': '饮食建议', '运动': '运动建议', '睡眠': '睡眠建议', '心理': '心理调适' };
  var needLogin = (category === '饮食' || category === '运动' || category === '睡眠');
  var guestBanner = '';
  if (needLogin && !isLoggedIn()) {
    guestBanner = '<div style="padding:12px 16px;background:rgba(184,134,38,0.08);border:1px solid rgba(184,134,38,0.2);border-radius:8px;margin-bottom:14px;display:flex;align-items:center;gap:10px;font-size:13px;color:#8A6318">' +
      '<i class="fa-solid fa-circle-info" style="font-size:16px"></i>' +
      '<span style="flex:1">登录并完善健康档案后，可获得基于您个人情况的<strong>个性化' + titles[category] + '</strong></span>' +
      '<button class="btn btn-primary btn-sm" onclick="window.location.href=\'/static/login.html\'" style="white-space:nowrap">去登录</button>' +
    '</div>';
  }
  var html = guestBanner + '<div id="lifestyleLoading" style="font-size:13px;color:var(--text-secondary);text-align:center;padding:20px">正在生成建议...</div>' +
    '<div id="lifestyleResult" style="display:none;font-size:14px;line-height:1.8;white-space:pre-wrap;"></div>';
  openModal(titles[category] || '生活建议', html);
  loadLifestyle(category);
}

async function loadLifestyle(category) {
  try {
    var data = await apiPost('/api/health/lifestyle', { session_id: sessionId, category: category });
    var loading = document.getElementById('lifestyleLoading');
    var result = document.getElementById('lifestyleResult');
    if (loading) loading.style.display = 'none';
    if (result) {
      result.style.display = 'block';
      var text = data.response;
      if (data.is_personalized) {
        text = '✅ 已根据您的健康档案生成个性化建议\n\n' + text;
      }
      result.textContent = text;
    }
  } catch (e) {
    var loading = document.getElementById('lifestyleLoading');
    if (loading) loading.textContent = '加载失败，请稍后重试';
  }
}

function openFoodModal() {
  openModal('拍食物分析',
    '<p style="font-size:13px;color:var(--text-secondary);margin-bottom:12px">上传食物图片，获取食物识别和基础饮食科普</p>' +
    '<input type="file" id="foodFileInput" accept="image/*" capture="environment" style="display:none" onchange="execFoodAnalysis(event)">' +
    '<button class="btn btn-primary" style="width:100%" onclick="document.getElementById(\'foodFileInput\').click()"><i class="fa-solid fa-camera"></i> 选择食物图片</button>');
}

async function execFoodAnalysis(event) {
  var file = event.target.files[0];
  if (!file) return;
  showModalResponse('正在识别食物...');
  var fd = new FormData();
  fd.append('file', file);
  fd.append('session_id', sessionId);
  try {
    var r = await fetch(API_BASE + '/api/health/food_analyze', { method: 'POST', body: fd });
    var d = await r.json();
    showModalResponse(d.response);
  } catch (e) { showModalResponse('分析失败'); }
  event.target.value = '';
}

/* ── Init ───────────────────────────────────────────────────────────────── */
document.getElementById('msgInput').addEventListener('keydown', function (e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMsg(); }
});

// Load session list on startup
loadSessionList();
loadProfile();

// Auto-restore last active session context on startup
(function autoRestoreSession() {
  var lastSid = localStorage.getItem('lastActiveSession');
  if (lastSid) {
    sessionId = lastSid;
    localStorage.setItem('sessionId', lastSid);
    loadContextFromStorage(lastSid);
    // Delay to let page render first, then load history
    setTimeout(function() {
      loadChatHistory(lastSid, true);
    }, 500);
  }
})();

// 监听页面可见性变化（从登录页返回时自动刷新）
document.addEventListener('visibilitychange', function() {
  if (document.visibilityState === 'visible') {
    console.log('[visibility] 页面可见，刷新会话列表');
    // 短暂延迟后重新加载会话列表和用户信息
    setTimeout(function() {
      loadSessionList();
      updateAuthUI();
      loadProfile();
    }, 200);
  }
});

// Save last active session before unload
window.addEventListener('beforeunload', function() {
  saveCurrentContext();
  localStorage.setItem('lastActiveSession', sessionId);
});
