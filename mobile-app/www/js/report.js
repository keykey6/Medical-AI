/* ── Report Page Logic ─────────────────────────────────────────────────── */

const sessionId = getSessionId();
let selectedFile = null;
let currentType = '其他报告';
let currentInterpretation = null;

// ── Report types ─────────────────────────────────────────────────────────
async function loadCategories() {
  try {
    const data = await apiGet('/api/report/categories');
    if (!data.categories) return;
    const grid = document.getElementById('typeGrid');
    let html = '';
    data.categories.forEach(cat => {
      html += `<div class="type-category">${cat.category}</div>`;
      cat.types.forEach(t => {
        const sel = t === currentType ? ' selected' : '';
        html += `<button class="type-btn${sel}" onclick="selectType('${escapeHtml(t)}')">${t}</button>`;
      });
    });
    grid.innerHTML = html;
  } catch { /* categories unavailable */ }
}

function selectType(type) {
  currentType = type;
  $$('.type-btn').forEach(b => {
    b.classList.toggle('selected', b.textContent.trim() === type);
  });
}

function selectQuickType(type) { selectType(type); }

// ── File handling ────────────────────────────────────────────────────────
function handleFileSelect(event) {
  const file = event.target.files[0];
  if (!file) return;
  if (!['image/jpeg','image/png','image/gif','image/bmp','image/webp'].includes(file.type)) {
    alert('不支持的图片格式，请上传JPG、PNG、GIF、BMP或WebP格式的图片'); return;
  }
  if (file.size > 15 * 1024 * 1024) {
    alert('图片大小超过15MB限制'); return;
  }
  selectedFile = file;
  const reader = new FileReader();
  reader.onload = function(e) {
    document.getElementById('previewImg').src = e.target.result;
    document.getElementById('uploadPreview').style.display = 'block';
    document.getElementById('uploadZone').style.display = 'none';
  };
  reader.readAsDataURL(file);
}

function clearUpload() {
  selectedFile = null;
  document.getElementById('uploadPreview').style.display = 'none';
  document.getElementById('uploadZone').style.display = 'block';
}

// ── Analysis ─────────────────────────────────────────────────────────────
async function submitAnalysis() {
  if (!selectedFile) { alert('请先上传报告图片'); return; }

  document.getElementById('loadingBlock').style.display = 'block';
  document.getElementById('resultCard').style.display = 'none';
  document.getElementById('analyzeBtn').disabled = true;

  const fd = new FormData();
  fd.append('file', selectedFile);
  fd.append('session_id', sessionId);
  fd.append('report_type', currentType);

  try {
    const r = await fetch('/api/report/analyze', { method: 'POST', body: fd });
    const data = await r.json();
    currentInterpretation = data.interpretation_result;
    document.getElementById('resultBody').textContent = data.interpretation_result;
    document.getElementById('resultCard').style.display = 'block';
    document.getElementById('followupResult').style.display = 'none';
    loadHistory();
  } catch (e) {
    alert('报告解读失败: ' + e.message);
  } finally {
    document.getElementById('loadingBlock').style.display = 'none';
    document.getElementById('analyzeBtn').disabled = false;
  }
}

// ── Follow-up ────────────────────────────────────────────────────────────
async function sendFollowup() {
  const msg = document.getElementById('followupInput').value.trim();
  if (!msg) return;

  document.getElementById('followupBtn').disabled = true;
  document.getElementById('followupInput').value = '';

  const div = document.getElementById('followupResult');
  div.style.display = 'block';
  div.textContent = '正在回复...';

  try {
    const data = await apiPost('/api/report/followup', {
      session_id: sessionId, message: msg,
    });
    div.textContent = '您：' + msg + '\n\n' + data.response;
  } catch {
    div.textContent = '提问失败，请稍后重试';
  } finally {
    document.getElementById('followupBtn').disabled = false;
    document.getElementById('followupInput').focus();
  }
}

function handleFollowupKey(event) {
  if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); sendFollowup(); }
}

// ── History ──────────────────────────────────────────────────────────────
async function loadHistory() {
  try {
    const data = await apiGet('/api/report/history/' + sessionId);
    const div = document.getElementById('historyList');
    if (data.records && data.records.length > 0) {
      div.innerHTML = data.records.map(r => `
        <div class="history-item" onclick="showDetail('${escapeHtml(r.interpretation_result || '')}')">
          <div class="history-type">${r.report_type}</div>
          <div class="history-time">${r.created_at}</div>
        </div>`).join('');
    } else {
      div.innerHTML = '<div class="empty-state"><i class="fa-solid fa-inbox empty-icon"></i><p>暂无解读记录</p></div>';
    }
  } catch { /* history unavailable */ }
}

function showDetail(content) {
  document.getElementById('detailContent').textContent = content || '无详细内容';
  document.getElementById('detailModal').classList.add('show');
}
function closeDetailModal() {
  document.getElementById('detailModal').classList.remove('show');
}

function resetPage() {
  clearUpload();
  currentInterpretation = null;
  document.getElementById('resultCard').style.display = 'none';
  document.getElementById('followupResult').style.display = 'none';
  document.getElementById('followupInput').value = '';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Drag & drop ──────────────────────────────────────────────────────────
const zone = document.getElementById('uploadZone');
zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
zone.addEventListener('drop', e => {
  e.preventDefault(); zone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) {
    const dt = new DataTransfer(); dt.items.add(file);
    document.getElementById('fileInput').files = dt.files;
    handleFileSelect({ target: { files: dt.files } });
  }
});

// ── Init ─────────────────────────────────────────────────────────────────
loadCategories();
loadHistory();
