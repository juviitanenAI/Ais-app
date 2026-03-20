import { state } from './state.js';
import { vesselTypeInfo, shipIcon } from './utils.js';
import { selectVessel } from './ui.js';

export const map = L.map('map', {
  zoomControl: false,
  attributionControl: true,
}).setView([60.5, 22.0], 7);

L.control.zoom({ position: 'topright' }).addTo(map);

const osmBase = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; <a href="https://openstreetmap.org">OSM</a>' });
const darkBase = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { maxZoom: 19, attribution: '&copy; <a href="https://carto.com">CARTO</a>' });
const seaMap = L.tileLayer('https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png', { maxZoom: 18, attribution: '&copy; <a href="https://openseamap.org">OpenSeaMap</a>', opacity: 0.8 });

darkBase.addTo(map);
seaMap.addTo(map);
L.control.layers({ 'Dark': darkBase, 'Light': osmBase }, { 'Nautical (OpenSeaMap)': seaMap }, { position: 'topright' }).addTo(map);

map.on('click', () => {
  if (window.innerWidth <= 768 && document.getElementById('app').classList.contains('sidebar-visible')) {
    document.getElementById('sidebar').classList.add('collapsed');
    document.getElementById('app').classList.remove('sidebar-visible');
  }
});

export function clearSelectionRing() {
  if (state.selectionRing) {
    map.removeLayer(state.selectionRing);
    state.selectionRing = null;
  }
}

export function showSelectionRing(latlng) {
  clearSelectionRing();
  state.selectionRing = L.marker(latlng, {
    icon: L.divIcon({ className: '', html: '<div class="selected-ring"></div>', iconSize: [36, 36], iconAnchor: [18, 18] }),
    interactive: false,
    zIndexOffset: -1,
  }).addTo(map);
}

export function clearHistory() {
  if (state.historyPolyline) {
    map.removeLayer(state.historyPolyline);
    state.historyPolyline = null;
  }
}

export function renderHistory(mmsi, points) {
  clearHistory();
  if (points.length < 2) return;
  const coords = points.map(p => [p.lat, p.lon]);
  const liveData = state.vessels[mmsi]?.data;
  if (liveData && liveData.lat != null && liveData.lon != null) {
    coords.push([liveData.lat, liveData.lon]);
  }
  const { color } = vesselTypeInfo(state.vessels[mmsi]?.data?.type);
  state.historyPolyline = L.polyline(coords, { color, weight: 3, opacity: 0.7, dashArray: '8, 4', lineJoin: 'round' }).addTo(map);
  points.forEach((p, i) => {
    const opacity = 0.3 + (i / points.length) * 0.7;
    const circle = L.circleMarker([p.lat, p.lon], { radius: 3, fillColor: color, fillOpacity: opacity, stroke: false }).addTo(map);
    const time = new Date(p.ts * 1000).toLocaleTimeString('fi-FI', { hour: '2-digit', minute: '2-digit' });
    circle.bindTooltip(`${time} — ${p.sog != null ? p.sog.toFixed(1) + ' kn' : ''}`, { className: '', direction: 'top' });
    if (!state.historyPolyline._circles) state.historyPolyline._circles = [];
    state.historyPolyline._circles.push(circle);
  });
  const origRemove = state.historyPolyline.onRemove.bind(state.historyPolyline);
  state.historyPolyline.onRemove = function(mapObj) {
    (this._circles || []).forEach(c => mapObj.removeLayer(c));
    origRemove(mapObj);
  };
}

export function addOrUpdateVessel(v) {
  const mmsi = v.mmsi;
  const { color } = vesselTypeInfo(v.type);
  const heading = v.heading ?? v.cog ?? 0;

  if (state.vessels[mmsi]) {
    const existing = state.vessels[mmsi];
    existing.data = v;
    existing.lastUpdate = Date.now();
    existing.marker.setLatLng([v.lat, v.lon]);
    existing.marker.setIcon(shipIcon(color, heading));
    existing.marker.setOpacity(1);
    
    if (mmsi === state.selectedMmsi) {
      if (state.selectionRing) state.selectionRing.setLatLng([v.lat, v.lon]);
      if (state.historyPolyline) {
        const latlngs = state.historyPolyline.getLatLngs();
        if (latlngs && latlngs.length > 0) {
          latlngs[latlngs.length - 1] = new L.LatLng(v.lat, v.lon);
          state.historyPolyline.setLatLngs(latlngs);
        }
      }
    }
  } else {
    const marker = L.marker([v.lat, v.lon], { icon: shipIcon(color, heading), title: v.name || mmsi }).addTo(map);
    marker.on('click', () => selectVessel(mmsi));
    marker.bindPopup('', { maxWidth: 240, autoPan: false });
    marker.on('popupopen', () => {
      const d = state.vessels[mmsi]?.data;
      if (!d) return;
      const ti = vesselTypeInfo(d.type);
      marker.setPopupContent(`
        <div class="popup-title">${d.name || '(Unknown)'}</div>
        <div class="popup-row"><span>MMSI</span><span>${d.mmsi}</span></div>
        <div class="popup-row"><span>Type</span><span>${ti.label}</span></div>
        <div class="popup-row"><span>SOG</span><span>${d.sog != null ? d.sog.toFixed(1) + ' kn' : '—'}</span></div>
        <div class="popup-row"><span>COG</span><span>${d.cog != null ? d.cog.toFixed(0) + '°' : '—'}</span></div>
        <div class="popup-row"><span>Heading</span><span>${d.heading != null ? d.heading.toFixed(0) + '°' : '—'}</span></div>
        <div class="popup-row"><span>Dest</span><span>${d.destination || '—'}</span></div>
      `);
    });
    state.vessels[mmsi] = { marker, data: v, lastUpdate: Date.now() };
  }
}

export function pruneStaleVessels(staleMinutes) {
  const cutoff = Date.now() - staleMinutes * 60 * 1000;
  for (const [mmsi, v] of Object.entries(state.vessels)) {
    if (v.lastUpdate < cutoff) {
      v.marker.setOpacity(0.3);
    }
  }
}
