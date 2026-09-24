// MyRide K12 Front-End Application Logic with Time-Based Gradient Route Map

let map = null;
let busMarker = null;
let startMarker = null;
let endMarker = null;
let latestCoords = null;
let isMapLoaded = false;
let selectedRouteDate = 'live'; // 'live' or 'YYYY-MM-DD'

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    fetchRouteDates();
    fetchStatus();
    fetchHistory();
    fetchStats();

    // Auto refresh every 3 seconds for live streaming feel
    setInterval(() => {
        if (selectedRouteDate === 'live') {
            fetchStatus();
            fetchHistory();
            fetchStats();
        }
    }, 3000);

    document.getElementById('btnRecenter').addEventListener('click', recenterMap);
    document.getElementById('btnRefreshHistory').addEventListener('click', () => {
        if (selectedRouteDate === 'live') {
            fetchHistory();
        } else {
            loadRouteForDate(selectedRouteDate);
        }
    });

    const routeSelect = document.getElementById('routeDateSelect');
    routeSelect.addEventListener('change', (e) => {
        selectedRouteDate = e.target.value;
        const modeTag = document.getElementById('routeModeTag');

        if (selectedRouteDate === 'live') {
            modeTag.textContent = 'Live View';
            modeTag.className = 'badge-tag';
            fetchHistory();
        } else {
            modeTag.textContent = `Route: ${selectedRouteDate}`;
            modeTag.className = 'badge-tag active-route';
            loadRouteForDate(selectedRouteDate);
        }
    });

    routeSelect.addEventListener('focus', fetchRouteDates);
});

function initMap() {
    // Default coords: Ardsley / Dobbs Ferry NY area from HAR capture
    const defaultLat = 41.0188408;
    const defaultLon = -73.8418884;

    // CARTO Vector Basemap Dark Matter style
    const vectorStyleUrl = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

    map = new maplibregl.Map({
        container: 'map',
        style: vectorStyleUrl,
        center: [defaultLon, defaultLat], // MapLibre uses [lng, lat]
        zoom: 14,
        attributionControl: false
    });

    map.addControl(new maplibregl.NavigationControl(), 'top-right');

    // Create custom HTML element for Bus Pin Marker
    const el = document.createElement('div');
    el.className = 'bus-marker-pin';
    el.innerHTML = '🚌';

    const popup = new maplibregl.Popup({ offset: 25 }).setHTML('<b>Bus Tracker</b><br>Initial Location');
    busMarker = new maplibregl.Marker({ element: el })
        .setLngLat([defaultLon, defaultLat])
        .setPopup(popup)
        .addTo(map);

    map.on('load', () => {
        isMapLoaded = true;

        // Add GeoJSON LineString source with lineMetrics enabled for gradient rendering
        map.addSource('route', {
            'type': 'geojson',
            'lineMetrics': true,
            'data': {
                'type': 'Feature',
                'properties': {},
                'geometry': {
                    'type': 'LineString',
                    'coordinates': []
                }
            }
        });

        // Base solid line layer for robust visibility
        map.addLayer({
            'id': 'route-line-base',
            'type': 'line',
            'source': 'route',
            'layout': {
                'line-join': 'round',
                'line-cap': 'round'
            },
            'paint': {
                'line-color': '#38bdf8',
                'line-width': 4,
                'line-opacity': 0.6
            }
        });

        // Top line layer with dynamic time-progress color gradient
        map.addLayer({
            'id': 'route-line',
            'type': 'line',
            'source': 'route',
            'layout': {
                'line-join': 'round',
                'line-cap': 'round'
            },
            'paint': {
                'line-width': 6,
                'line-gradient': [
                    'interpolate',
                    ['linear'],
                    ['line-progress'],
                    0.0, '#38bdf8',  // Trip Start (Sky Blue)
                    0.25, '#3b82f6', // Royal Blue
                    0.50, '#a855f7', // Vibrant Purple
                    0.75, '#ec4899', // Hot Pink
                    1.00, '#ef4444'  // Trip End (Coral Red)
                ]
            }
        });

        if (selectedRouteDate !== 'live') {
            loadRouteForDate(selectedRouteDate);
        }
    });
}

function recenterMap() {
    if (latestCoords && map) {
        map.flyTo({
            center: [latestCoords.lon, latestCoords.lat],
            zoom: 15,
            essential: true
        });
    }
}

async function fetchRouteDates() {
    try {
        const resp = await fetch('/api/routes/dates');
        if (!resp.ok) return;
        const dates = await resp.json();

        const select = document.getElementById('routeDateSelect');
        const currentVal = select.value;
        select.innerHTML = '<option value="live">Live / Recent Stream</option>';

        dates.forEach(d => {
            const opt = document.createElement('option');
            opt.value = d;
            opt.textContent = `Route: ${d}`;
            select.appendChild(opt);
        });

        if (currentVal && Array.from(select.options).some(o => o.value === currentVal)) {
            select.value = currentVal;
        }
    } catch (err) {
        console.warn('Error fetching route dates:', err);
    }
}

async function fetchStatus() {
    try {
        const resp = await fetch('/api/status');
        if (!resp.ok) return;
        const data = await resp.json();

        updateStatusBadge(data);
        updateStudentCard(data.student);

        if (data.latest_location && selectedRouteDate === 'live') {
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
    windowPill.querySelector('span').textContent = 'Mon-Fri 7:45 AM - 8:50 AM ET';

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

    if (loc.log_time) {
        try {
            const dateObj = new Date(loc.log_time);
            document.getElementById('statLogTime').textContent = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        } catch (e) {
            document.getElementById('statLogTime').textContent = loc.log_time.split('T')[1]?.split('.')[0] || loc.log_time;
        }
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

    latestCoords = { lat, lon };
    if (busMarker) {
        busMarker.setLngLat([lon, lat]);
        busMarker.getPopup().setHTML(`
            <b>Bus #${loc.asset_unique_id || '53'}</b><br>
            Speed: ${Math.round(loc.speed || 0)} mph<br>
            Time: ${loc.log_time ? formatTimeStr(loc.log_time) : 'N/A'}
        `);
    }
}

async function fetchHistory() {
    try {
        const resp = await fetch('/api/locations?limit=100');
        if (!resp.ok) return;
        const locations = await resp.json();

        renderHistoryTable(locations);
        renderRoutePolyline(locations, true);
    } catch (err) {
        console.warn('Error fetching history:', err);
    }
}

async function loadRouteForDate(dateStr) {
    try {
        const resp = await fetch(`/api/routes/by-date?date=${encodeURIComponent(dateStr)}`);
        if (!resp.ok) return;
        const routeData = await resp.json();

        renderHistoryTable(routeData.locations);
        renderRoutePolyline(routeData.locations, false);
    } catch (err) {
        console.warn(`Error loading route for ${dateStr}:`, err);
    }
}

function renderHistoryTable(locations) {
    const tbody = document.getElementById('historyTableBody');
    if (!locations || locations.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-cell">No bus location points recorded for this selection.</td></tr>';
        return;
    }

    tbody.innerHTML = locations.map(r => {
        let timeStr = formatTimeStr(r.log_time || r.received_at);
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
    }).join('');
}

function renderRoutePolyline(locations, isLive) {
    if (!map || !isMapLoaded) return;

    if (!locations || locations.length === 0) {
        const routeSource = map.getSource('route');
        if (routeSource) {
            routeSource.setData({
                'type': 'Feature',
                'properties': {},
                'geometry': { 'type': 'LineString', 'coordinates': [] }
            });
        }
        clearWaypointMarkers();
        updateSummaryBar(0, 0, '--:--', '--:--');
        return;
    }

    // Sort locations in chronological ascending order
    const chronoLocations = [...locations].sort((a, b) => {
        const timeA = new Date(a.log_time || a.received_at || 0);
        const timeB = new Date(b.log_time || b.received_at || 0);
        return timeA - timeB;
    });

    const coordinates = chronoLocations
        .filter(r => r.latitude && r.longitude)
        .map(r => [r.longitude, r.latitude]);

    if (coordinates.length === 0) return;

    // Update GeoJSON route line source
    const routeSource = map.getSource('route');
    if (routeSource) {
        routeSource.setData({
            'type': 'Feature',
            'properties': {},
            'geometry': {
                'type': 'LineString',
                'coordinates': coordinates
            }
        });

        // Trigger line-gradient paint property update for MapLibre GL JS
        if (map.getLayer('route-line')) {
            map.setPaintProperty('route-line', 'line-gradient', [
                'interpolate',
                ['linear'],
                ['line-progress'],
                0.0, '#38bdf8',  // Trip Start (Sky Blue)
                0.25, '#3b82f6', // Royal Blue
                0.50, '#a855f7', // Vibrant Purple
                0.75, '#ec4899', // Hot Pink
                1.00, '#ef4444'  // Trip End (Coral Red)
            ]);
        }
    }

    // Calculate total distance & time range
    const distanceMiles = calculateRouteDistanceMiles(coordinates);
    const startTimeStr = formatTimeStr(chronoLocations[0].log_time || chronoLocations[0].received_at);
    const endTimeStr = formatTimeStr(chronoLocations[chronoLocations.length - 1].log_time || chronoLocations[chronoLocations.length - 1].received_at);

    updateSummaryBar(chronoLocations.length, distanceMiles, startTimeStr, endTimeStr);

    // Update Bus Marker & Location Card to latest point of route
    if (!isLive && chronoLocations.length > 0) {
        const lastLoc = chronoLocations[chronoLocations.length - 1];
        updateLocationCard(lastLoc);
        updateMapPosition(lastLoc);
    }

    // Set Waypoint Start/End Markers
    clearWaypointMarkers();

    if (coordinates.length > 1) {
        const startPoint = coordinates[0];
        const endPoint = coordinates[coordinates.length - 1];

        // 🟢 Start Waypoint Marker
        const startEl = document.createElement('div');
        startEl.className = 'start-marker-pin';
        startEl.innerHTML = '🟢';
        startEl.title = `Start: ${startTimeStr}`;

        const startPopup = new maplibregl.Popup({ offset: 20 })
            .setHTML(`<b>Trip Start</b><br>Time: ${startTimeStr}`);

        startMarker = new maplibregl.Marker({ element: startEl })
            .setLngLat(startPoint)
            .setPopup(startPopup)
            .addTo(map);

        // 🔴 End Waypoint Marker
        const endEl = document.createElement('div');
        endEl.className = 'end-marker-pin';
        endEl.innerHTML = isLive ? '🏁' : '🔴';
        endEl.title = `End: ${endTimeStr}`;

        const endPopup = new maplibregl.Popup({ offset: 20 })
            .setHTML(`<b>Trip End</b><br>Time: ${endTimeStr}`);

        endMarker = new maplibregl.Marker({ element: endEl })
            .setLngLat(endPoint)
            .setPopup(endPopup)
            .addTo(map);
    }

    // Fit map bounds to show full route path if specific date selected
    if (!isLive && coordinates.length > 0) {
        const bounds = new maplibregl.LngLatBounds();
        coordinates.forEach(coord => bounds.extend(coord));
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
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
        Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
}

function formatTimeStr(isoOrRaw) {
    if (!isoOrRaw) return 'N/A';
    try {
        if (isoOrRaw.includes('T')) {
            const parts = isoOrRaw.split('T');
            const timePart = parts[1].split('.')[0];
            return `${parts[0]} ${timePart}`;
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
