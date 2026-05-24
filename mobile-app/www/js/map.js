/* ── Map Page Logic — Baidu Maps ───────────────────────────────────────── */

var sessionId = getSessionId();
var bmap = null;
var markers = [];
var userMarker = null;
var infoWindow = null;
var hospitals = [];
var userLat = null, userLng = null;
var selectedIdx = -1;

var DEFAULT_LAT = 39.915;
var DEFAULT_LNG = 116.404;

// ── Load & Init ──────────────────────────────────────────────────────────
window.onBMapLoaded = function () {
  bmap = new BMap.Map('mapContainer');
  bmap.centerAndZoom(new BMap.Point(DEFAULT_LNG, DEFAULT_LAT), 12);
  bmap.enableScrollWheelZoom(true);
  bmap.addControl(new BMap.NavigationControl({ anchor: BMAP_ANCHOR_TOP_LEFT }));
  bmap.addControl(new BMap.ScaleControl({ anchor: BMAP_ANCHOR_BOTTOM_LEFT }));
  infoWindow = new BMap.InfoWindow('');

  bmap.addEventListener('click', function () {
    infoWindow.close();
    selectedIdx = -1;
    updateListHighlight();
  });

  loadFilters();
  doSearch();
};

function loadBaiduMaps() {
  fetch('/api/map/ak')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      var script = document.createElement('script');
      script.src = 'https://api.map.baidu.com/api?v=3.0&ak=' + data.ak + '&callback=onBMapLoaded';
      document.head.appendChild(script);
    })
    .catch(function () {
      document.getElementById('mapContainer').innerHTML =
        '<div class="empty-state" style="height:100%;display:flex;align-items:center;justify-content:center">' +
        '<div><i class="fa-solid fa-circle-exclamation empty-icon"></i><p>百度地图加载失败</p></div></div>';
    });
}

// ── Markers ──────────────────────────────────────────────────────────────
function clearMarkers() {
  markers.forEach(function (m) { bmap.removeOverlay(m); });
  markers = [];
  if (userMarker) { bmap.removeOverlay(userMarker); userMarker = null; }
}

function renderMarkers(list) {
  clearMarkers();
  if (!bmap) return;
  if (!list || !list.length) return;

  var bounds = [];
  var iconSize = new BMap.Size(28, 36);

  list.forEach(function (h, i) {
    if (!h.lat || !h.lng) return;
    var pt = new BMap.Point(h.lng, h.lat);
    bounds.push(pt);

    // Create colored pin marker
    var icon = new BMap.Icon(
      'https://api.map.baidu.com/img/markers.png',
      new BMap.Size(23, 31),
      {
        anchor: new BMap.Size(11, 31),
        imageOffset: new BMap.Size(-(i % 10) * 23, -(Math.floor(i / 10)) * 31)
      }
    );
    // Fallback: simple red circle marker via inline SVG
    var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="36" viewBox="0 0 28 36">' +
      '<path d="M14 0C6.3 0 0 6.3 0 14c0 10.5 14 22 14 22s14-11.5 14-22C28 6.3 21.7 0 14 0z" fill="#4F46E5"/>' +
      '<circle cx="14" cy="13" r="6" fill="white"/>' +
      '<text x="14" y="16" text-anchor="middle" fill="#4F46E5" font-size="10" font-weight="bold">' + (i + 1) + '</text></svg>';

    var iconUrl = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
    var markerIcon = new BMap.Icon(iconUrl, iconSize);

    var marker = new BMap.Marker(pt, { icon: markerIcon });
    (function (idx) {
      marker.addEventListener('click', function () { selectHospital(idx); });
    })(i);

    bmap.addOverlay(marker);
    markers.push(marker);
  });

  if (bounds.length > 0) {
    try {
      bmap.setViewport(bounds, { margins: [40, 40, 40, 40] });
    } catch (e) {
      bmap.centerAndZoom(bounds[0], 13);
    }
  }
}

// ── User location ────────────────────────────────────────────────────────
function showUserLocation(lat, lng) {
  if (!bmap) return;
  if (userMarker) bmap.removeOverlay(userMarker);
  var pt = new BMap.Point(lng, lat);
  userMarker = new BMap.Marker(pt, {
    icon: new BMap.Icon(
      'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(
        '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 20 20">' +
        '<circle cx="10" cy="10" r="8" fill="#3B82F6" stroke="white" stroke-width="2"/>' +
        '<circle cx="10" cy="10" r="3" fill="white"/></svg>'),
      new BMap.Size(20, 20)
    )
  });
  bmap.addOverlay(userMarker);
  bmap.panTo(pt);
}

// ── Hospital selection ───────────────────────────────────────────────────
function selectHospital(i) {
  selectedIdx = i;
  var h = hospitals[i];
  if (!h || !bmap) return;

  var pt = new BMap.Point(h.lng, h.lat);
  bmap.panTo(pt);

  var depts = h.departments;
  if (Array.isArray(depts)) depts = depts.slice(0, 8).join(', ');
  if (!depts) depts = '-';

  var html =
    '<div style="font-family:sans-serif;max-width:260px">' +
    '<div style="font-weight:600;font-size:15px;margin-bottom:10px;color:#1a1a2e">' + escapeHtml(h.name) + '</div>' +
    '<div style="font-size:12px;color:#5c5c7b;margin-bottom:4px"><b>等级：</b>' + escapeHtml(h.level || '-') + '</div>' +
    '<div style="font-size:12px;color:#5c5c7b;margin-bottom:4px"><b>地址：</b>' + escapeHtml(h.address || '-') + '</div>' +
    '<div style="font-size:12px;color:#5c5c7b;margin-bottom:4px"><b>电话：</b><span style="color:#4F46E5">' + escapeHtml(h.phone || '-') + '</span></div>' +
    '<div style="font-size:12px;color:#5c5c7b;margin-bottom:4px"><b>科室：</b>' + depts + '</div>' +
    '<div style="font-size:12px;color:#5c5c7b;margin-top:8px">' + escapeHtml(h.desc || '') + '</div>' +
    (h.distance ? '<div style="font-size:11px;color:#8b8ba0;margin-top:6px">约 ' + h.distance + ' km</div>' : '') +
    '</div>';

  infoWindow.setContent(html);
  bmap.openInfoWindow(infoWindow, pt);
  updateListHighlight();
}

function updateListHighlight() {
  var items = document.querySelectorAll('.hospital-item');
  items.forEach(function (el, i) { el.classList.toggle('active', i === selectedIdx); });
}

// ── Search ───────────────────────────────────────────────────────────────
function doSearch() {
  var city = document.getElementById('citySelect').value;
  var dept = document.getElementById('departmentSelect').value;
  var level = document.getElementById('levelSelect').value;
  var keyword = document.getElementById('keywordInput').value;

  fetch('/api/map/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      lat: userLat || DEFAULT_LAT,
      lng: userLng || DEFAULT_LNG,
      city: city || null,
      department: dept || null,
      level: level || null,
      keyword: keyword || null,
    }),
  })
    .then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(function (data) {
      hospitals = data.hospitals || [];
      document.getElementById('resultCount').textContent = hospitals.length;

      if (!hospitals.length) {
        document.getElementById('hospitalList').innerHTML =
          '<div class="empty-state"><i class="fa-solid fa-circle-exclamation empty-icon"></i><p>未找到符合条件的医院</p></div>';
      } else {
        document.getElementById('hospitalList').innerHTML = hospitals.map(function (h, i) {
          return '<div class="hospital-item" onclick="selectHospital(' + i + ')">' +
            '<div class="hosp-name">' + h.name + '</div>' +
            '<div class="hosp-addr">' + (h.address || '') + '</div>' +
            '<div class="hosp-tags">' +
            (h.level ? '<span class="hosp-tag ht-level">' + h.level + '</span>' : '') +
            (h.distance ? '<span class="hosp-tag ht-dist">约' + h.distance + 'km</span>' : '') +
            '</div></div>';
        }).join('');
      }

      renderMarkers(hospitals);
      selectedIdx = -1;
      if (infoWindow) infoWindow.close();
    })
    .catch(function () {
      document.getElementById('hospitalList').innerHTML =
        '<div class="empty-state"><i class="fa-solid fa-circle-exclamation empty-icon"></i><p>搜索失败</p></div>';
      document.getElementById('resultCount').textContent = '0';
    });
}

// ── Geolocation ──────────────────────────────────────────────────────────
function getUserLocation() {
  document.getElementById('locationText').textContent = '正在获取位置...';

  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        userLat = pos.coords.latitude;
        userLng = pos.coords.longitude;
        document.getElementById('locationText').textContent =
          '已定位 (' + userLat.toFixed(4) + ', ' + userLng.toFixed(4) + ')';
        showUserLocation(userLat, userLng);
        doSearch();
      },
      function () { tryBaiduGeolocation(); },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  } else {
    tryBaiduGeolocation();
  }
}

function tryBaiduGeolocation() {
  if (!bmap || !BMap.Geolocation) {
    document.getElementById('locationText').textContent = '定位失败，使用默认位置（北京）';
    return;
  }
  var geo = new BMap.Geolocation();
  geo.getCurrentPosition(function (r) {
    if (r && r.point) {
      userLat = r.point.lat;
      userLng = r.point.lng;
      document.getElementById('locationText').textContent =
        '已定位 (' + userLat.toFixed(4) + ', ' + userLng.toFixed(4) + ')';
      showUserLocation(userLat, userLng);
      doSearch();
    } else {
      document.getElementById('locationText').textContent = '定位失败，使用默认位置（北京）';
    }
  });
}

// ── Filter loading ───────────────────────────────────────────────────────
function loadFilters() {
  Promise.all([
    fetch('/api/map/departments').then(function (r) { return r.json(); }),
    fetch('/api/map/levels').then(function (r) { return r.json(); }),
    fetch('/api/map/cities').then(function (r) { return r.json(); }),
  ]).then(function (results) {
    populateSelect('departmentSelect', results[0].departments);
    populateSelect('levelSelect', results[1].levels);
    populateSelect('citySelect', results[2].cities);
  }).catch(function () { /* filters unavailable */ });
}

function populateSelect(id, items) {
  var sel = document.getElementById(id);
  items.forEach(function (v) {
    var o = document.createElement('option');
    o.value = v;
    o.textContent = v;
    sel.appendChild(o);
  });
}

// ── Init ─────────────────────────────────────────────────────────────────
document.getElementById('keywordInput').addEventListener('keyup', function (e) {
  if (e.key === 'Enter') doSearch();
});

['citySelect', 'departmentSelect', 'levelSelect'].forEach(function (id) {
  document.getElementById(id).addEventListener('change', function () {
    doSearch();
  });
});

loadBaiduMaps();
