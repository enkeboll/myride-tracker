// MyRide K12 Front-End Application Logic with CARTO Vector Basemaps & MapLibre GL

let map = null;
let busMarker = null;
let latestCoords = null;
let isMapLoaded = false;

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    fetchStatus();
    fetchHistory();
    fetchStats();

    // Auto refresh every 3 seconds for live streaming feel
    setInterval(() => {
        fetchStatus();
        fetchHistory();
        fetchStats();
    }, 3000);

    document.getElementById('btnRecenter').addEventListener('click', recenterMap);
    document.getElementById('btnRefreshHistory').addEventListener('click', fetchHistory);
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
        // Add GeoJSON LineString source & layer for route breadcrumb trail
        map.addSource('route', {
            'type': 'geojson',
            'data': {
                'type': 'Feature',
                'properties': {},
                'geometry': {
                    'type': 'LineString',
                    'coordinates': []
                }
            }
        });

        map.addLayer({
            'id': 'route',
            'type': 'line',
            'source': 'route',
            'layout': {
                'line-join': 'round',
                'line-cap': 'round'
            },
            'paint': {
                'line-color': '#38bdf8',
                'line-width': 4,
                'line-opacity': 0.85
            }
        });
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

async function fetchStatus() {
    try {
        const resp = await fetch('/api/status');
        if (!resp.ok) return;
        const data = await resp.json();

        updateStatusBadge(data);
        updateStudentCard(data.student);

        if (data.latest_location) {
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
            Time: ${loc.log_time ? loc.log_time.split('T')[1]?.split('.')[0] : 'N/A'}
        `);
    }
}

async function fetchHistory() {
    try {
        const resp = await fetch('/api/locations?limit=50');
        if (!resp.ok) return;
        const locations = await resp.json();

        renderHistoryTable(locations);
        renderRoutePolyline(locations);
    } catch (err) {
        console.warn('Error fetching history:', err);
    }
}

function renderHistoryTable(locations) {
    const tbody = document.getElementById('historyTableBody');
    if (!locations || locations.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-cell">No bus location points recorded yet.</td></tr>';
        return;
    }

    tbody.innerHTML = locations.map(r => {
        let timeStr = r.log_time || r.received_at || 'N/A';
        if (timeStr.includes('T')) {
            const parts = timeStr.split('T');
            timeStr = `${parts[0]} ${parts[1].split('.')[0]}`;
        }
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

function renderRoutePolyline(locations) {
    if (!map || !isMapLoaded || !locations || locations.length === 0) return;

    // Filter valid coords and reverse to get chronological path [lng, lat]
    const points = locations
        .filter(r => r.latitude && r.longitude)
        .map(r => [r.longitude, r.latitude])
        .reverse();

    const routeSource = map.getSource('route');
    if (routeSource) {
        routeSource.setData({
            'type': 'Feature',
            'properties': {},
            'geometry': {
                'type': 'LineString',
                'coordinates': points
            }
        });
    }
}

async function fetchStats() {
    try {
        const resp = await fetch('/api/stats');
        if (!resp.ok) return;
        const data = await resp.json();

        document.getElementById('statTotalPoints').textContent = data.total_points || 0;
        document.getElementById('statMaxSpeed').textContent = `Max Speed: ${Math.round(data.max_speed || 0)} mph`;
    } catch (err) {
        console.warn('Error fetching stats:', err);
    }
}
