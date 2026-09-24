// MyRide K12 Front-End Application Logic with Interactive Time Scrubber & Calendar Navigation

let map = null;
let busMarker = null;
let startMarker = null;
let endMarker = null;
let latestCoords = null;
let isMapLoaded = false;
let selectedRouteDate = 'live'; // 'live' or 'YYYY-MM-DD'

let isDebugMode = false;
let isOffHours = false;
let hasInitializedDefaultDate = false;

let historyCurrentPage = 1;
let historyTotalPages = 1;
let historyTotalCount = 0;
let historyPageSize = 20;
let historySearchQuery = '';
let historyMinSpeed = 0;

let staticMarkers = [];

function checkAndSetOffHoursDefaultDate() {
  if (hasInitializedDefaultDate) return;

  if (isOffHours && availableDates.length > 0 && selectedRouteDate === 'live') {
    hasInitializedDefaultDate = true;
    const latestDate = availableDates[availableDates.length - 1];
    selectRouteDate(latestDate);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  // Check for debug mode flag in URL query parameters (?debug=true or ?debug=1)
  const urlParams = new URLSearchParams(window.location.search);
  const debugVal = urlParams.get('debug');
  isDebugMode = debugVal === 'true' || debugVal === '1' || urlParams.has('debug');

  const historyCard = document.getElementById('historyCard');
  const mainLayout = document.querySelector('.main-layout');

  if (isDebugMode) {
    if (historyCard) historyCard.classList.remove('hidden');
    if (mainLayout) mainLayout.classList.remove('full-width-map');
  } else {
    if (historyCard) historyCard.classList.add('hidden');
    if (mainLayout) mainLayout.classList.add('full-width-map');
  }

  initMap();
  fetchRouteDates();
  fetchStatus();
  if (isDebugMode) {
    fetchHistory(1);
  }
  fetchStats();
  fetchStaticLocations();

  // History Filtering & Pagination Event Listeners
  const searchInput = document.getElementById('historySearchInput');
  const speedFilter = document.getElementById('historySpeedFilter');
  const pageSizeSelect = document.getElementById('historyPageSizeSelect');
  const btnPrev = document.getElementById('historyBtnPrev');
  const btnNext = document.getElementById('historyBtnNext');

  if (searchInput) {
    let debounceTimer = null;
    searchInput.addEventListener('input', (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        historySearchQuery = e.target.value.trim();
        historyCurrentPage = 1;
        fetchHistory(1);
      }, 300);
    });
  }

  if (speedFilter) {
    speedFilter.addEventListener('change', (e) => {
      historyMinSpeed = parseFloat(e.target.value) || 0;
      historyCurrentPage = 1;
      fetchHistory(1);
    });
  }

  if (pageSizeSelect) {
    pageSizeSelect.addEventListener('change', (e) => {
      historyPageSize = parseInt(e.target.value, 10) || 20;
      historyCurrentPage = 1;
      fetchHistory(1);
    });
  }

  if (btnPrev) {
    btnPrev.addEventListener('click', () => {
      if (historyCurrentPage > 1) {
        historyCurrentPage--;
        fetchHistory(historyCurrentPage);
      }
    });
  }

  if (btnNext) {
    btnNext.addEventListener('click', () => {
      if (historyCurrentPage < historyTotalPages) {
        historyCurrentPage++;
        fetchHistory(historyCurrentPage);
      }
    });
  }

  // Auto refresh every 3 seconds for live streaming feel
  setInterval(() => {
    if (selectedRouteDate === 'live' && !isPinned) {
      fetchStatus();
      if (isDebugMode) {
        fetchHistory(historyCurrentPage);
      }
      fetchStats();
    }
  }, 3000);

  document.getElementById('btnRecenter').addEventListener('click', () => {
    unpinTimeline();
    recenterMap();
  });

  document.getElementById('btnRefreshHistory').addEventListener('click', () => {
    unpinTimeline();
    if (selectedRouteDate === 'live') {
      fetchHistory();
    } else {
      loadRouteForDate(selectedRouteDate);
    }
  });

  // Calendar Datepicker & Navigation Listeners
  const datePicker = document.getElementById('routeDatePicker');
  const btnPrevDay = document.getElementById('btnPrevDay');
  const btnNextDay = document.getElementById('btnNextDay');
  const btnLiveToggle = document.getElementById('btnLiveToggle');

  datePicker.addEventListener('change', (e) => {
    const val = e.target.value;
    if (val) {
      selectRouteDate(val);
    }
  });

  btnPrevDay.addEventListener('click', () => {
    jumpToAdjacentDate(-1);
  });

  btnNextDay.addEventListener('click', () => {
    jumpToAdjacentDate(1);
  });

  btnLiveToggle.addEventListener('click', () => {
    switchToLiveView();
  });

  // Setup Interactive Time Gradient Scrubber Controls
  setupInteractiveTimeline();
});

function initMap() {
  // Default center & zoom encompassing typical bus route area (from 2026-09-16 analysis)
  const defaultLat = 41.002254;
  const defaultLon = -73.84874;

  // CARTO Vector Basemap Dark Matter style
  const vectorStyleUrl = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

  map = new maplibregl.Map({
    container: 'map',
    style: vectorStyleUrl,
    center: [defaultLon, defaultLat], // MapLibre uses [lng, lat]
    zoom: 13, // Fits the ~3.5mi x 2.2mi route area perfectly
    attributionControl: false,
  });

  map.addControl(new maplibregl.NavigationControl(), 'top-right');

  // Create custom HTML element for Top-Down School Bus Marker
  const el = document.createElement('div');
  el.className = 'bus-marker-pin';
  el.innerHTML = `
        <svg class="bus-svg" viewBox="0 0 32 56" fill="none" xmlns="http://www.w3.org/2000/svg">
          <!-- Drop Shadow / Glow -->
          <rect x="3" y="6" width="26" height="46" rx="8" fill="#000000" opacity="0.45" filter="blur(3px)"/>

          <!-- Side Mirrors (Left & Right) -->
          <rect x="0" y="12" width="3" height="6" rx="1.5" fill="#0f172a"/>
          <rect x="29" y="12" width="3" height="6" rx="1.5" fill="#0f172a"/>

          <!-- Bus Body (Classic School Bus Yellow) -->
          <rect x="3" y="4" width="26" height="48" rx="8" fill="#facc15" stroke="#eab308" stroke-width="2"/>

          <!-- Front Curved Hood Accent -->
          <path d="M7 4 H25 V9 C25 11, 7 11, 7 9 Z" fill="#eab308"/>

          <!-- Directional Arrow on Hood -->
          <path d="M16 5 L11 10 H21 Z" fill="#ffffff" opacity="0.95"/>

          <!-- Front Windshield -->
          <path d="M6 12 C6 11, 26 11, 26 12 L25 16 C25 17, 7 17, 7 16 Z" fill="#0f172a"/>

          <!-- Side Window Strips (Left & Right) -->
          <rect x="4.5" y="19" width="2" height="26" rx="1" fill="#1e293b"/>
          <rect x="25.5" y="19" width="2" height="26" rx="1" fill="#1e293b"/>

          <!-- Roof Emergency Escape Hatch & Roof Ridges -->
          <rect x="11" y="24" width="10" height="11" rx="2" fill="#ca8a04" stroke="#a16207" stroke-width="1.5"/>
          <line x1="8" y1="20" x2="24" y2="20" stroke="#ca8a04" stroke-width="1.5"/>
          <line x1="8" y1="39" x2="24" y2="39" stroke="#ca8a04" stroke-width="1.5"/>

          <!-- Rear Window -->
          <rect x="7" y="47" width="18" height="3" rx="1" fill="#0f172a"/>

          <!-- Rear Red Stop / Brake Lights -->
          <circle cx="6.5" cy="50" r="1.8" fill="#ef4444"/>
          <circle cx="25.5" cy="50" r="1.8" fill="#ef4444"/>
        </svg>
    `;

  const popup = new maplibregl.Popup({ offset: 30 }).setHTML('<b>Bus Tracker</b><br>Initial Location');
  busMarker = new maplibregl.Marker({
    element: el,
    rotationAlignment: 'map',
    pitchAlignment: 'map',
  })
    .setLngLat([defaultLon, defaultLat])
    .setPopup(popup)
    .addTo(map);

  map.on('load', () => {
    isMapLoaded = true;

    // Add GeoJSON LineString source with lineMetrics enabled for gradient rendering
    map.addSource('route', {
      type: 'geojson',
      lineMetrics: true,
      data: {
        type: 'Feature',
        properties: {},
        geometry: {
          type: 'LineString',
          coordinates: [],
        },
      },
    });

    // Base solid line layer for robust visibility
    map.addLayer({
      id: 'route-line-base',
      type: 'line',
      source: 'route',
      layout: {
        'line-join': 'round',
        'line-cap': 'round',
      },
      paint: {
        'line-color': '#38bdf8',
        'line-width': 4,
        'line-opacity': 0.6,
      },
    });

    // Top line layer with dynamic time-progress color gradient
    map.addLayer({
      id: 'route-line',
      type: 'line',
      source: 'route',
      layout: {
        'line-join': 'round',
        'line-cap': 'round',
      },
      paint: {
        'line-width': 6,
        'line-gradient': [
          'interpolate',
          ['linear'],
          ['line-progress'],
          0.0,
          '#38bdf8', // Trip Start (Sky Blue)
          0.25,
          '#3b82f6', // Royal Blue
          0.5,
          '#a855f7', // Vibrant Purple
          0.75,
          '#ec4899', // Hot Pink
          1.0,
          '#ef4444', // Trip End (Coral Red)
        ],
      },
    });

    if (selectedRouteDate !== 'live') {
      loadRouteForDate(selectedRouteDate);
    }
  });
}

async function fetchStaticLocations() {
  try {
    const resp = await fetch('/api/student/locations');
    if (!resp.ok) return;
    const locations = await resp.json();
    renderStaticMarkers(locations);
  } catch (err) {
    console.warn('Error fetching static student locations:', err);
  }
}

function renderStaticMarkers(locations) {
  staticMarkers.forEach((m) => m.remove());
  staticMarkers = [];

  locations.forEach((loc) => {
    const el = document.createElement('div');
    el.className = `static-marker-pin ${loc.type}`;

    let iconSvg = '';
    if (loc.type === 'school') {
      iconSvg = `
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 10v6M2 10l10-5 10 5-10 5z"></path>
                    <path d="M6 12v5c0 2 2 3 6 3s6-1 6-3v-5"></path>
                </svg>`;
    } else if (loc.type === 'home') {
      iconSvg = `
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                    <polyline points="9 22 9 12 15 12 15 22"></polyline>
                </svg>`;
    } else if (loc.type === 'stop') {
      iconSvg = `
                <svg viewBox="0 0 24 24" width="22" height="22">
                    <polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86" fill="#ef4444" stroke="#dc2626" stroke-width="1.5"/>
                    <text x="12" y="15" font-family="Inter, sans-serif" font-size="6" font-weight="900" fill="#ffffff" text-anchor="middle">STOP</text>
                </svg>`;
    }

    el.innerHTML = `
            <div class="marker-badge ${loc.type}" title="${loc.title}">
                ${iconSvg}
            </div>
        `;

    const popupHtml = `
            <div class="static-popup ${loc.type}-popup">
                <div class="popup-header">
                    <span class="popup-type-tag ${loc.type}">${loc.type.toUpperCase()}</span>
                </div>
                <div class="popup-title">${loc.title}</div>
                <div class="popup-sub">${loc.subtitle}</div>
                <div class="popup-addr">📍 ${loc.address}</div>
            </div>
        `;

    const popup = new maplibregl.Popup({ offset: 20 }).setHTML(popupHtml);
    const marker = new maplibregl.Marker({ element: el })
      .setLngLat([loc.longitude, loc.latitude])
      .setPopup(popup)
      .addTo(map);

    staticMarkers.push(marker);
  });
}

let fpInstance = null;

async function fetchRouteDates() {
  try {
    const resp = await fetch('/api/routes/dates');
    if (!resp.ok) return;
    const dates = await resp.json();

    // Store sorted ascending ('2026-09-14' ... '2026-09-23')
    availableDates = dates.sort();

    initDatePicker();
    updateDateNavButtons();

    checkAndSetOffHoursDefaultDate();
  } catch (err) {
    console.warn('Error fetching route dates:', err);
  }
}

function initDatePicker() {
  if (typeof flatpickr === 'undefined') return;

  if (fpInstance) {
    fpInstance.destroy();
  }

  fpInstance = flatpickr('#routeDatePicker', {
    theme: 'dark',
    dateFormat: 'Y-m-d',
    enable: availableDates, // Greys out & disables dates without data
    onChange: function (selectedDates, dateStr) {
      if (dateStr) {
        selectRouteDate(dateStr);
      }
    },
    onDayCreate: function (dObj, dStr, fp, dayElem) {
      const dateObj = dayElem.dateObj;
      const year = dateObj.getFullYear();
      const month = String(dateObj.getMonth() + 1).padStart(2, '0');
      const day = String(dateObj.getDate()).padStart(2, '0');
      const formatted = `${year}-${month}-${day}`;

      if (availableDates.includes(formatted)) {
        dayElem.classList.add('has-data-day');
        const dot = document.createElement('span');
        dot.className = 'data-dot';
        dayElem.appendChild(dot);
      }
    },
  });
}

function selectRouteDate(dateStr) {
  selectedRouteDate = dateStr;
  unpinTimeline();

  const modeTag = document.getElementById('routeModeTag');
  const btnLive = document.getElementById('btnLiveToggle');

  if (fpInstance && dateStr !== 'live') {
    fpInstance.setDate(dateStr, false);
  }

  btnLive.className = 'btn btn-sm btn-live'; // Deactivate live

  if (availableDates.includes(dateStr)) {
    modeTag.textContent = `Route: ${dateStr}`;
    modeTag.className = 'badge-tag active-route';
    loadRouteForDate(dateStr);
  } else {
    modeTag.textContent = `No Data: ${dateStr}`;
    modeTag.className = 'badge-tag standby';
    renderHistoryTable([]);
    renderRoutePolyline(null, [], 0.0, false);
  }

  updateDateNavButtons();
}

function switchToLiveView() {
  selectedRouteDate = 'live';
  unpinTimeline();

  const modeTag = document.getElementById('routeModeTag');
  const btnLive = document.getElementById('btnLiveToggle');

  if (fpInstance) {
    fpInstance.clear();
  }

  btnLive.className = 'btn btn-sm btn-live active';
  modeTag.textContent = 'Live View';
  modeTag.className = 'badge-tag';

  updateDateNavButtons();
  fetchHistory();
}

function jumpToAdjacentDate(direction) {
  if (availableDates.length === 0) return;

  if (selectedRouteDate === 'live') {
    // If in live view and clicking prev (-1), jump to latest available date
    if (direction < 0) {
      selectRouteDate(availableDates[availableDates.length - 1]);
    }
    return;
  }

  const idx = availableDates.indexOf(selectedRouteDate);
  if (direction < 0) {
    // Find largest date < selectedRouteDate
    let prevDate = null;
    for (let i = availableDates.length - 1; i >= 0; i--) {
      if (availableDates[i] < selectedRouteDate) {
        prevDate = availableDates[i];
        break;
      }
    }
    if (prevDate) selectRouteDate(prevDate);
  } else if (direction > 0) {
    // Find smallest date > selectedRouteDate
    let nextDate = null;
    for (let i = 0; i < availableDates.length; i++) {
      if (availableDates[i] > selectedRouteDate) {
        nextDate = availableDates[i];
        break;
      }
    }
    if (nextDate) selectRouteDate(nextDate);
  }
}

function updateDateNavButtons() {
  const btnPrev = document.getElementById('btnPrevDay');
  const btnNext = document.getElementById('btnNextDay');

  if (availableDates.length === 0) {
    btnPrev.disabled = true;
    btnNext.disabled = true;
    return;
  }

  if (selectedRouteDate === 'live') {
    btnPrev.disabled = false; // Prev jumps to latest date with data
    btnNext.disabled = true; // In live view, no "next" date
    return;
  }

  const hasPrev = availableDates.some((d) => d < selectedRouteDate);
  const hasNext = availableDates.some((d) => d > selectedRouteDate);

  btnPrev.disabled = !hasPrev;
  btnNext.disabled = !hasNext;
}

function setupInteractiveTimeline() {
  const wrapper = document.getElementById('gradientBarWrapper');
  const scrubber = document.getElementById('gradientScrubber');
  const tooltip = document.getElementById('timelineTooltip');

  if (!wrapper || !scrubber || !tooltip) return;

  wrapper.addEventListener('mousemove', (e) => {
    if (!currentRouteLocations || currentRouteLocations.length === 0) return;

    const rect = wrapper.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const idx = Math.round(pct * (currentRouteLocations.length - 1));
    const loc = currentRouteLocations[idx];

    if (!loc) return;

    // Position scrubber & tooltip along gradient bar
    scrubber.classList.remove('hidden');
    tooltip.classList.remove('hidden');

    scrubber.style.left = `${pct * 100}%`;
    tooltip.style.left = `${pct * 100}%`;

    const timeStr = formatShortTimeStr(loc.log_time || loc.received_at);
    const speedStr = loc.speed !== null ? `${Math.round(loc.speed)} mph` : '0 mph';

    if (isPinned && pinnedIndex === idx) {
      tooltip.textContent = `📍 Pinned: ${timeStr} (${speedStr})`;
    } else {
      tooltip.textContent = `${timeStr} • ${speedStr}`;
    }

    // Preview bus location on map
    updateLocationCard(loc);
    updateMapPosition(loc);
  });

  wrapper.addEventListener('click', (e) => {
    if (!currentRouteLocations || currentRouteLocations.length === 0) return;

    const rect = wrapper.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const idx = Math.round(pct * (currentRouteLocations.length - 1));
    const loc = currentRouteLocations[idx];

    if (!loc) return;

    isPinned = true;
    pinnedIndex = idx;

    scrubber.classList.add('pinned');
    const timeStr = formatShortTimeStr(loc.log_time || loc.received_at);
    const speedStr = loc.speed !== null ? `${Math.round(loc.speed)} mph` : '0 mph';

    tooltip.textContent = `📍 Pinned: ${timeStr} (${speedStr})`;

    updateLocationCard(loc);
    updateMapPosition(loc);

    // Open popup on map for pinned location
    if (busMarker) {
      busMarker.getPopup().setHTML(`
                <b>📍 Pinned Location</b><br>
                Bus #${loc.asset_unique_id || '53'}<br>
                Time: ${timeStr}<br>
                Speed: ${speedStr}
            `);
      if (!busMarker.getPopup().isOpen()) {
        busMarker.togglePopup();
      }
    }
  });

  wrapper.addEventListener('mouseleave', () => {
    if (isPinned && pinnedIndex >= 0 && currentRouteLocations[pinnedIndex]) {
      const loc = currentRouteLocations[pinnedIndex];
      const pct = pinnedIndex / Math.max(1, currentRouteLocations.length - 1);
      scrubber.style.left = `${pct * 100}%`;
      tooltip.style.left = `${pct * 100}%`;
      const timeStr = formatShortTimeStr(loc.log_time || loc.received_at);
      const speedStr = loc.speed !== null ? `${Math.round(loc.speed)} mph` : '0 mph';
      tooltip.textContent = `📍 Pinned: ${timeStr} (${speedStr})`;
      updateLocationCard(loc);
      updateMapPosition(loc);
    } else {
      scrubber.classList.add('hidden');
      tooltip.classList.add('hidden');
      scrubber.classList.remove('pinned');

      if (selectedRouteDate === 'live' && currentRouteLocations.length > 0) {
        const latest = currentRouteLocations[currentRouteLocations.length - 1];
        updateLocationCard(latest);
        updateMapPosition(latest);
      }
    }
  });
}

function unpinTimeline() {
  isPinned = false;
  pinnedIndex = -1;
  const scrubber = document.getElementById('gradientScrubber');
  const tooltip = document.getElementById('timelineTooltip');
  if (scrubber) {
    scrubber.classList.add('hidden');
    scrubber.classList.remove('pinned');
  }
  if (tooltip) {
    tooltip.classList.add('hidden');
  }
}

function recenterMap() {
  if (latestCoords && map) {
    map.flyTo({
      center: [latestCoords.lon, latestCoords.lat],
      zoom: 15,
      essential: true,
    });
  }
}

async function fetchStatus() {
  try {
    const resp = await fetch('/api/status');
    if (!resp.ok) return;
    const data = await resp.json();

    isOffHours = !data.is_active_window;

    updateStatusBadge(data);
    updateStudentCard(data.student);

    if (isOffHours && !hasInitializedDefaultDate) {
      checkAndSetOffHoursDefaultDate();
    } else if (data.latest_location && selectedRouteDate === 'live' && !isPinned) {
      updateLocationCard(data.latest_location);
      updateMapPosition(data.latest_location);
    }
  } catch (err) {
    console.warn('Error fetching status:', err);
  }
}

function updateStatusBadge(data) {
  const badge = document.getElementById('statusBadge');
  const statusText = document.getElementById('statusText');
  const noticeBanner = document.getElementById('noticeBanner');
  const noticeText = document.getElementById('noticeText');
  const windowPill = document.getElementById('windowPill');

  const isActive = data.is_active_window;
  windowPill.querySelector('span').textContent = 'Mon-Fri 7:45 AM - 9:15 AM ET';

  if (isActive) {
    badge.className = 'status-badge';
    statusText.textContent = 'ACTIVE (STREAMING)';
    noticeBanner.classList.add('hidden');
  } else {
    badge.className = 'status-badge standby';
    statusText.textContent = 'STANDBY (OFF-HOURS)';
    noticeBanner.classList.remove('hidden');
    noticeText.textContent = `Outside active bus window (${data.status_message}). Showing recent recorded locations.`;
  }
}

function updateStudentCard(student) {
  if (!student) return;
  const busNum = student.active_vehicle ? `Bus #${student.active_vehicle}` : 'Bus #--';
  document.getElementById('statBusNumber').textContent = busNum;

  const studentName = `${student.first_name || ''} ${student.last_name || ''}`.trim();
  const locName = student.location_name ? ` (${student.location_name})` : '';
  document.getElementById('statStudentName').textContent = `Student: ${studentName}${locName}`;
}

function updateLocationCard(loc) {
  const speed = loc.speed !== null ? Math.round(loc.speed) : 0;
  document.getElementById('statSpeed').innerHTML = `${speed} <small>mph</small>`;

  const heading = loc.heading !== null ? `${Math.round(loc.heading)}°` : 'N/A';
  document.getElementById('statHeading').textContent = `Heading: ${heading}`;

  if (loc.log_time || loc.received_at) {
    document.getElementById('statLogTime').textContent = formatShortTimeStr(loc.log_time || loc.received_at);
  }

  if (loc.received_at) {
    const recvDate = new Date(loc.received_at);
    const diffSec = Math.floor((new Date() - recvDate) / 1000);
    let timeAgo = `${diffSec}s ago`;
    if (diffSec > 60) timeAgo = `${Math.floor(diffSec / 60)}m ago`;
    document.getElementById('statReceivedAgo').textContent = `Updated: ${timeAgo}`;
  }
}

function updateMapPosition(loc) {
  if (!loc || !loc.latitude || !loc.longitude) return;
  const lat = loc.latitude;
  const lon = loc.longitude;
  const heading = loc.heading !== null && loc.heading !== undefined ? loc.heading : 0;

  latestCoords = { lat, lon };
  if (busMarker) {
    busMarker.setLngLat([lon, lat]);
    busMarker.setRotation(heading);
    busMarker.getPopup().setHTML(`
            <b>Bus #${loc.asset_unique_id || '53'}</b><br>
            Speed: ${Math.round(loc.speed || 0)} mph<br>
            Heading: ${Math.round(heading)}°<br>
            Time: ${formatShortTimeStr(loc.log_time || loc.received_at)}
        `);
  }
}

async function fetchHistory(page = historyCurrentPage) {
  if (!isDebugMode) return;

  try {
    const url = `/api/locations?page=${page}&limit=${historyPageSize}&search=${encodeURIComponent(
      historySearchQuery
    )}&min_speed=${historyMinSpeed}`;
    const resp = await fetch(url);
    if (!resp.ok) return;
    const data = await resp.json();

    const items = data.items || data;
    historyCurrentPage = data.page || page;
    historyTotalPages = data.total_pages || 1;
    historyTotalCount = data.total_count !== undefined ? data.total_count : items.length;

    renderHistoryTable(items);
    updateHistoryPaginationUI();

    if (selectedRouteDate === 'live') {
      renderRoutePolyline(null, items, 0.0, true);
    }
  } catch (err) {
    console.warn('Error fetching history:', err);
  }
}

function updateHistoryPaginationUI() {
  const infoEl = document.getElementById('historyPaginationInfo');
  const btnPrev = document.getElementById('historyBtnPrev');
  const btnNext = document.getElementById('historyBtnNext');

  if (infoEl) {
    infoEl.textContent = `Page ${historyCurrentPage} of ${historyTotalPages} (${historyTotalCount} items)`;
  }

  if (btnPrev) {
    btnPrev.disabled = historyCurrentPage <= 1;
  }

  if (btnNext) {
    btnNext.disabled = historyCurrentPage >= historyTotalPages;
  }
}

async function loadRouteForDate(dateStr) {
  try {
    const resp = await fetch(`/api/routes/by-date?date=${encodeURIComponent(dateStr)}`);
    if (!resp.ok) return;
    const routeData = await resp.json();

    renderHistoryTable(routeData.locations);
    renderRoutePolyline(routeData.vector_coords, routeData.locations, routeData.distance_miles, false);
  } catch (err) {
    console.warn(`Error loading route for ${dateStr}:`, err);
  }
}

function renderHistoryTable(locations) {
  const tbody = document.getElementById('historyTableBody');
  if (!locations || locations.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="5" class="empty-cell">No bus location points recorded for this selection.</td></tr>';
    return;
  }

  tbody.innerHTML = locations
    .map((r) => {
      let timeStr = formatShortTimeStr(r.log_time || r.received_at);
      const speedStr = r.speed !== null ? `${Math.round(r.speed)} mph` : '0 mph';
      const latStr = r.latitude ? r.latitude.toFixed(5) : '--';
      const lonStr = r.longitude ? r.longitude.toFixed(5) : '--';

      return `
            <tr>
                <td>${timeStr}</td>
                <td><strong>#${r.asset_unique_id}</strong></td>
                <td>${latStr}</td>
                <td>${lonStr}</td>
                <td><span class="speed-badge">${speedStr}</span></td>
            </tr>
        `;
    })
    .join('');
}

function renderRoutePolyline(vectorCoords, locations, serverDistanceMiles, isLive) {
  if (!map || !isMapLoaded) return;

  let coordinates =
    vectorCoords && vectorCoords.length > 0
      ? vectorCoords
      : (locations || []).filter((r) => r.latitude && r.longitude).map((r) => [r.longitude, r.latitude]);

  if (!coordinates || coordinates.length === 0) {
    currentRouteLocations = [];
    const routeSource = map.getSource('route');
    if (routeSource) {
      routeSource.setData({
        type: 'Feature',
        properties: {},
        geometry: { type: 'LineString', coordinates: [] },
      });
    }
    clearWaypointMarkers();
    updateSummaryBar(0, 0, '--:--', '--:--');
    return;
  }

  // Sort location records chronologically for status/timeline scrubbing
  const chronoLocations = [...(locations || [])].sort((a, b) => {
    const timeA = new Date(a.log_time || a.received_at || 0);
    const timeB = new Date(b.log_time || b.received_at || 0);
    return timeA - timeB;
  });

  currentRouteLocations =
    chronoLocations.length > 0
      ? chronoLocations
      : coordinates.map((c, i) => ({
          latitude: c[1],
          longitude: c[0],
          speed: 0,
          heading: 0,
          log_time: null,
        }));

  if (!isPinned) {
    unpinTimeline();
  }

  // Update GeoJSON route line source with street-snapped vector geometry
  const routeSource = map.getSource('route');
  if (routeSource) {
    routeSource.setData({
      type: 'Feature',
      properties: {},
      geometry: {
        type: 'LineString',
        coordinates: coordinates,
      },
    });

    // Trigger line-gradient paint property update for MapLibre GL JS
    if (map.getLayer('route-line')) {
      map.setPaintProperty('route-line', 'line-gradient', [
        'interpolate',
        ['linear'],
        ['line-progress'],
        0.0,
        '#38bdf8', // Trip Start (Sky Blue)
        0.25,
        '#3b82f6', // Royal Blue
        0.5,
        '#a855f7', // Vibrant Purple
        0.75,
        '#ec4899', // Hot Pink
        1.0,
        '#ef4444', // Trip End (Coral Red)
      ]);
    }
  }

  // Calculate total distance & time range
  const distanceMiles = serverDistanceMiles || calculateRouteDistanceMiles(coordinates);
  const startTimeStr =
    chronoLocations.length > 0
      ? formatShortTimeStr(chronoLocations[0].log_time || chronoLocations[0].received_at)
      : '--:--';
  const endTimeStr =
    chronoLocations.length > 0
      ? formatShortTimeStr(
          chronoLocations[chronoLocations.length - 1].log_time ||
            chronoLocations[chronoLocations.length - 1].received_at
        )
      : '--:--';

  updateSummaryBar(chronoLocations.length, distanceMiles, startTimeStr, endTimeStr);

  // Update Timeline Start/End Labels
  const startLabelEl = document.getElementById('legendStartTime');
  const endLabelEl = document.getElementById('legendEndTime');
  if (startLabelEl) startLabelEl.textContent = `🌅 ${startTimeStr}`;
  if (endLabelEl) endLabelEl.textContent = `🌆 ${endTimeStr}`;

  // Update Bus Marker & Location Card to latest point of route if not pinned
  if (!isLive && chronoLocations.length > 0 && !isPinned) {
    const lastLoc = chronoLocations[chronoLocations.length - 1];
    updateLocationCard(lastLoc);
    updateMapPosition(lastLoc);
  }

  // Set Waypoint Start/End Markers ONLY
  clearWaypointMarkers();

  if (coordinates.length > 1) {
    const startPoint = coordinates[0];
    const endPoint = coordinates[coordinates.length - 1];

    // 🟢 Start Waypoint Marker
    const startEl = document.createElement('div');
    startEl.className = 'start-marker-pin';
    startEl.innerHTML = '🟢';
    startEl.title = `Start: ${startTimeStr}`;

    const startPopup = new maplibregl.Popup({ offset: 20 }).setHTML(`<b>Trip Start</b><br>Time: ${startTimeStr}`);

    startMarker = new maplibregl.Marker({ element: startEl }).setLngLat(startPoint).setPopup(startPopup).addTo(map);

    // 🔴 End Waypoint Marker
    const endEl = document.createElement('div');
    endEl.className = 'end-marker-pin';
    endEl.innerHTML = isLive ? '🏁' : '🔴';
    endEl.title = `End: ${endTimeStr}`;

    const endPopup = new maplibregl.Popup({ offset: 20 }).setHTML(`<b>Trip End</b><br>Time: ${endTimeStr}`);

    endMarker = new maplibregl.Marker({ element: endEl }).setLngLat(endPoint).setPopup(endPopup).addTo(map);
  }

  // Fit map bounds to show full route path if specific date selected
  if (!isLive && coordinates.length > 0 && !isPinned) {
    const bounds = new maplibregl.LngLatBounds();
    coordinates.forEach((coord) => bounds.extend(coord));
    map.fitBounds(bounds, { padding: 60, maxZoom: 16 });
  }
}

function clearWaypointMarkers() {
  if (startMarker) {
    startMarker.remove();
    startMarker = null;
  }
  if (endMarker) {
    endMarker.remove();
    endMarker = null;
  }
}

function updateSummaryBar(pointCount, distanceMiles, startTime, endTime) {
  document.getElementById('routePointCount').textContent = pointCount;
  document.getElementById('routeDistance').textContent = `${distanceMiles.toFixed(2)} mi`;
  document.getElementById('routeTimeRange').textContent = `${startTime} → ${endTime}`;
}

function calculateRouteDistanceMiles(coords) {
  let total = 0;
  for (let i = 0; i < coords.length - 1; i++) {
    total += haversineMiles(coords[i][1], coords[i][0], coords[i + 1][1], coords[i + 1][0]);
  }
  return total;
}

function haversineMiles(lat1, lon1, lat2, lon2) {
  const R = 3958.8; // Radius of the Earth in miles
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

function formatShortTimeStr(isoOrRaw) {
  if (!isoOrRaw) return '--:--';
  try {
    const d = new Date(isoOrRaw);
    if (!isNaN(d.getTime())) {
      return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    }
    if (isoOrRaw.includes('T')) {
      const timePart = isoOrRaw.split('T')[1].split('.')[0];
      const [h, m] = timePart.split(':');
      const hour = parseInt(h, 10);
      const ampm = hour >= 12 ? 'PM' : 'AM';
      const h12 = hour % 12 || 12;
      return `${h12}:${m} ${ampm}`;
    }
    return isoOrRaw;
  } catch (e) {
    return isoOrRaw;
  }
}

async function fetchStats() {
  try {
    const resp = await fetch('/api/stats');
    if (!resp.ok) return;
    const data = await resp.json();

    const totalPtsEl = document.getElementById('statTotalPoints');
    if (totalPtsEl) totalPtsEl.textContent = data.total_points || 0;

    const maxSpdEl = document.getElementById('statMaxSpeed');
    if (maxSpdEl) maxSpdEl.textContent = `Max Speed: ${Math.round(data.max_speed || 0)} mph`;
  } catch (err) {
    console.warn('Error fetching stats:', err);
  }
}
