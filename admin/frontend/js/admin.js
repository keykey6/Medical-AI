/* ═══════════════════════════════════════════════════════════════════════════
   Admin — Main App Logic (Dashboard / Sessions / Compliance / QoS / System)
   ═══════════════════════════════════════════════════════════════════════════ */

var SC_ICONS = {
  teal: 'sc-icon-teal', gold: 'sc-icon-gold', blue: 'sc-icon-blue',
  amber: 'sc-icon-amber', rose: 'sc-icon-rose', green: 'sc-icon-green',
};

function renderStatCards(containerId, cards) {
  var el = document.getElementById(containerId);
  if (!el) return;
  var html = '';
  cards.forEach(function (c) {
    html += '<div class="stat-card">' +
      '<div class="stat-card-icon ' + (SC_ICONS[c.color] || 'sc-icon-teal') + '"><i class="fa-solid ' + c.icon + '"></i></div>' +
      '<div class="stat-val">' + c.value + '</div>' +
      '<div class="stat-lbl">' + c.label + '</div>' +
    '</div>';
  });
  el.innerHTML = html;
}

/* ── Dashboard ──────────────────────────────────────────────────────── */
function loadDashboard() {
  destroyCharts();
  adminApi('/dashboard/stats', 'GET').then(function (data) {
    if (data.cards) renderStatCards('statCards', data.cards);

    // Pie chart for message types
    var dist = data.message_type_distribution || {};
    var labels = Object.keys(dist);
    var values = Object.values(dist);
    var colors = [CHART_COLORS.teal, CHART_COLORS.gold, CHART_COLORS.blue, CHART_COLORS.rose, CHART_COLORS.amber, CHART_COLORS.green];
    if (labels.length) makeDoughnutChart('chartMsgType', labels, values, colors.slice(0, labels.length));
  }).catch(function (e) { console.error(e); });

  adminApi('/dashboard/trends', 'GET').then(function (data) {
    var days = (data.days || []).map(function (d) { return d.slice(5); }); // MM-DD
    makeLineChart('chartTrend', days, [
      { label: '对话数', data: data.chat_counts || [], borderColor: CHART_COLORS.teal, backgroundColor: CHART_COLORS.tealBg, tension: 0.3, fill: true, pointRadius: 3 },
      { label: '活跃会话', data: data.session_counts || [], borderColor: CHART_COLORS.gold, backgroundColor: CHART_COLORS.goldBg, tension: 0.3, fill: true, pointRadius: 3 },
    ]);
  }).catch(function (e) { console.error(e); });
}

/* ── Sessions ───────────────────────────────────────────────────────── */
function loadSessions() {
  destroyCharts();
  adminApi('/sessions/analytics', 'GET').then(function (data) {
    renderStatCards('sessionStatCards', [
      { label: '总会话', value: String(data.total_sessions || 0), icon: 'fa-folder-tree', color: 'teal' },
      { label: '活跃会话', value: String(data.active_sessions || 0), icon: 'fa-comments', color: 'gold' },
      { label: '匿名会话', value: String(data.anonymous_sessions || 0), icon: 'fa-ghost', color: 'amber' },
      { label: '认证会话', value: String(data.authenticated_sessions || 0), icon: 'fa-user-check', color: 'blue' },
      { label: '匿名率', value: (data.summary && data.summary.anonymous_rate || 0) + '%', icon: 'fa-chart-line', color: 'rose' },
    ]);

    // Depth distribution bar chart
    var depth = data.depth_distribution || {};
    var dLabels = Object.keys(depth);
    var dValues = Object.values(depth);
    if (dLabels.length) {
      makeBarChart('chartDepth', dLabels, [
        { label: '会话数', data: dValues, backgroundColor: [CHART_COLORS.teal, CHART_COLORS.gold, CHART_COLORS.amber, CHART_COLORS.rose], borderRadius: 6 },
      ]);
    }

    // Hourly distribution
    var hourly = data.hourly_24h || {};
    var hLabels = Object.keys(hourly).map(function (h) { return h + ':00'; });
    var hValues = Object.values(hourly);
    if (hLabels.length) {
      makeBarChart('chartHourly', hLabels, [
        { label: '活跃会话数', data: hValues, backgroundColor: CHART_COLORS.teal, borderRadius: 4 },
      ]);
    }
  }).catch(function (e) { console.error(e); });
}

/* ── Compliance ─────────────────────────────────────────────────────── */
function loadCompliance() {
  destroyCharts();
  adminApi('/compliance/summary', 'GET').then(function (data) {
    renderStatCards('complianceStatCards', [
      { label: '拦截+转人工合计', value: String(data.blocked_count || 0), icon: 'fa-ban', color: 'rose' },
      { label: '分诊触发', value: String(data.triage_count || 0), icon: 'fa-stethoscope', color: 'teal' },
      { label: '总消息', value: String(data.total_count || 0), icon: 'fa-envelope', color: 'blue' },
      { label: '拦截率', value: (data.block_rate_pct || 0) + '%', icon: 'fa-shield-halved', color: 'gold' },
    ]);

    var byType = data.by_type || {};
    var labels = Object.keys(byType);
    var values = Object.values(byType);
    if (labels.length) {
      makeBarChart('chartCompliance', labels, [
        { label: '次数', data: values, backgroundColor: [CHART_COLORS.rose, CHART_COLORS.amber, CHART_COLORS.gold], borderRadius: 6 },
      ]);
    }
  }).catch(function (e) { console.error(e); });
}

/* ── QoS ────────────────────────────────────────────────────────────── */
function loadQos() {
  destroyCharts();
  adminApi('/qos/metrics', 'GET').then(function (data) {
    var rtd = data.report_type_distribution || {};
    renderStatCards('qosStatCards', [
      { label: '24h拦截', value: String(data.recent_24h_blocks || 0), icon: 'fa-clock', color: 'amber' },
      { label: '报告类型数', value: String(Object.keys(rtd).length), icon: 'fa-file-medical', color: 'rose' },
    ]);

    var labels = Object.keys(rtd);
    var values = Object.values(rtd);
    if (labels.length) {
      makeBarChart('chartReportTypes', labels, [
        { label: '解读次数', data: values, backgroundColor: CHART_COLORS.gold, borderRadius: 6 },
      ]);
    }
  }).catch(function (e) { console.error(e); });
}

/* ── System ─────────────────────────────────────────────────────────── */
function loadSystem() {
  destroyCharts();
  adminApi('/system/health', 'GET').then(function (data) {
    var svc = data.services || {};
    var html = '';
    Object.keys(svc).forEach(function (name) {
      var status = svc[name];
      var cls = status === 'healthy' ? 'status-healthy' : status === 'degraded' ? 'status-degraded' : 'status-unreachable';
      var statusText = status === 'healthy' ? '正常' : status === 'degraded' ? '降级' : '不可达';
      html += '<div class="health-card">' +
        '<div class="health-status ' + cls + '"></div>' +
        '<div class="health-info"><div class="hl-name">' + name + '</div><div class="hl-status">' + statusText + '</div></div>' +
      '</div>';
    });
    // Add knowledge info
    var kn = data.knowledge || {};
    html += '<div class="health-card">' +
      '<div class="health-status status-healthy"></div>' +
      '<div class="health-info"><div class="hl-name">Knowledge Base</div><div class="hl-status">' + (kn.entry_count || 0) + ' 条记录</div></div>' +
    '</div>';
    document.getElementById('healthGrid').innerHTML = html;
  }).catch(function (e) { console.error(e); });

  adminApi('/system/config', 'GET').then(function (data) {
    var cfg = data.config || {};
    var html = '<tr><th>配置项</th><th>值</th></tr>';
    Object.keys(cfg).forEach(function (k) {
      html += '<tr><td>' + k + '</td><td>' + escapeHtml(String(cfg[k])) + '</td></tr>';
    });
    document.getElementById('configTable').innerHTML = html;
  }).catch(function (e) { console.error(e); });
}

// ── Init ─────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  if (localStorage.getItem('admin_token')) {
    loadDashboard();
    startAutoRefresh();
  }
});
