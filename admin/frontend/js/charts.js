/* ═══════════════════════════════════════════════════════════════════════════
   Admin — Chart.js Initialization (Light / Cream Theme)
   ═══════════════════════════════════════════════════════════════════════════ */

var _charts = {};

function destroyCharts() {
  Object.values(_charts).forEach(function (c) { c.destroy(); });
  _charts = {};
}

var CHART_COLORS = {
  teal: 'rgba(13,148,136,0.75)',
  tealBg: 'rgba(13,148,136,0.10)',
  gold: 'rgba(184,134,38,0.75)',
  goldBg: 'rgba(184,134,38,0.10)',
  blue: 'rgba(37,99,235,0.70)',
  blueBg: 'rgba(37,99,235,0.08)',
  rose: 'rgba(225,29,72,0.75)',
  roseBg: 'rgba(225,29,72,0.08)',
  amber: 'rgba(217,119,6,0.75)',
  amberBg: 'rgba(217,119,6,0.10)',
  green: 'rgba(22,163,74,0.75)',
  greenBg: 'rgba(22,163,74,0.10)',
};

function makeLineChart(canvasId, labels, datasets) {
  var ctx = document.getElementById(canvasId);
  if (!ctx) return;
  _charts[canvasId] = new Chart(ctx, {
    type: 'line',
    data: { labels: labels, datasets: datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            color: '#5C5346',
            font: { size: 11 },
            usePointStyle: true,
            padding: 20,
          },
        },
      },
      scales: {
        x: {
          ticks: { color: '#8A8276', font: { size: 10 } },
          grid: { color: 'rgba(140,120,90,0.08)' },
        },
        y: {
          ticks: { color: '#8A8276', font: { size: 10 } },
          grid: { color: 'rgba(140,120,90,0.08)' },
        },
      },
    },
  });
}

function makeBarChart(canvasId, labels, datasets) {
  var ctx = document.getElementById(canvasId);
  if (!ctx) return;
  _charts[canvasId] = new Chart(ctx, {
    type: 'bar',
    data: { labels: labels, datasets: datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            color: '#5C5346',
            font: { size: 11 },
            usePointStyle: true,
            padding: 20,
          },
        },
      },
      scales: {
        x: {
          ticks: { color: '#8A8276', font: { size: 10 } },
          grid: { display: false },
        },
        y: {
          ticks: { color: '#8A8276', font: { size: 10 } },
          grid: { color: 'rgba(140,120,90,0.08)' },
        },
      },
    },
  });
}

function makeDoughnutChart(canvasId, labels, data, colors) {
  var ctx = document.getElementById(canvasId);
  if (!ctx) return;
  _charts[canvasId] = new Chart(ctx, {
    type: 'doughnut',
    data: { labels: labels, datasets: [{ data: data, backgroundColor: colors, borderWidth: 0 }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: '#5C5346',
            font: { size: 11 },
            padding: 18,
            usePointStyle: true,
          },
        },
      },
    },
  });
}
