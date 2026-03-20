import { state } from './state.js';
import { vesselTypeInfo, shipIcon } from './utils.js';
import { selectVessel } from './ui.js';
import { map } from './map_instance.js';

L.control.zoom({ position: 'topright' }).addTo(map);

const osmBase = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; <a href="https://openstreetmap.org">OSM</a>' });
const darkBase = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { maxZoom: 19, attribution: '&copy; <a href="https://carto.com">CARTO</a>' });
const seaMap = L.tileLayer('https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png', { maxZoom: 18, attribution: '&copy; <a href="https://openseamap.org">OpenSeaMap</a>', opacity: 0.8 });

osmBase.addTo(map);
seaMap.addTo(map);
L.control.layers({ 'Light': osmBase, 'Dark': darkBase }, { 'Nautical (OpenSeaMap)': seaMap }, { position: 'topright' }).addTo(map);

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

export function clearHistory(mmsi = null) {
  if (mmsi) {
    const layer = state.historyLayers.get(mmsi);
    if (layer) {
      map.removeLayer(layer.polyline);
      (layer.circles || []).forEach(c => map.removeLayer(c));
      state.historyLayers.delete(mmsi);
    }
  } else {
    state.historyLayers.forEach((layer) => {
      map.removeLayer(layer.polyline);
      (layer.circles || []).forEach(c => map.removeLayer(c));
    });
    state.historyLayers.clear();
  }
}

export function renderHistory(mmsi, points) {
  clearHistory(mmsi);
  if (points.length < 2) return;

  const coords = points.map(p => [p.lat, p.lon]);
  const liveData = state.vessels[mmsi]?.data;
  if (liveData && liveData.lat != null && liveData.lon != null) {
    coords.push([liveData.lat, liveData.lon]);
  }

  const { color } = vesselTypeInfo(state.vessels[mmsi]?.data?.type, state.vessels[mmsi]?.data?.vtype_info);
  const isActive = (mmsi === state.activeMmsi);
  
  const polyline = L.polyline(coords, {
    color,
    weight: isActive ? 3 : 2,
    opacity: isActive ? 0.7 : 0.4,
    dashArray: isActive ? '8, 4' : '4, 4',
    lineJoin: 'round',
    smoothFactor: 1.5 // Performance optimization
  }).addTo(map);

  const circles = [];
  // Only render point circles for the active vessel to save performance
  if (isActive) {
    points.forEach((p, i) => {
      const opacity = 0.3 + (i / points.length) * 0.7;
      const circle = L.circleMarker([p.lat, p.lon], {
        radius: 3,
        fillColor: color,
        fillOpacity: opacity,
        stroke: false
      }).addTo(map);
      
      const time = new Date(p.ts * 1000).toLocaleTimeString('fi-FI', { hour: '2-digit', minute: '2-digit' });
      circle.bindTooltip(`${time} — ${p.sog != null ? p.sog.toFixed(1) + ' kn' : ''}`, { direction: 'top' });
      circles.push(circle);
    });
  }

  state.historyLayers.set(mmsi, { polyline, circles });
}

export function addOrUpdateVessel(v) {
  const mmsi = v.mmsi;
  const { color } = vesselTypeInfo(v.type, v.vtype_info);
  const heading = v.heading ?? v.cog ?? 0;
  const isPinned = state.selectedMmsis.has(mmsi);
  const isActive = (mmsi === state.activeMmsi);

  if (state.vessels[mmsi]) {
    const existing = state.vessels[mmsi];
    existing.data = v;
    existing.lastUpdate = Date.now();
    existing.marker.setLatLng([v.lat, v.lon]);
    existing.marker.setIcon(shipIcon(color, heading, isPinned, isActive));
    existing.marker.setOpacity(1);
    
    // Refresh popup if open
    if (existing.marker.getPopup() && existing.marker.isPopupOpen()) {
      updatePopupContent(existing.marker, v);
    }

    // Sync visibility with current filters
    updateMarkerVisibility(existing.marker, v);

    if (mmsi === state.activeMmsi || state.selectedMmsis.has(mmsi)) {
      if (mmsi === state.activeMmsi && state.selectionRing) {
        state.selectionRing.setLatLng([v.lat, v.lon]);
      }
      const layer = state.historyLayers.get(mmsi);
      if (layer) {
        const latlngs = layer.polyline.getLatLngs();
        if (latlngs && latlngs.length > 0) {
          latlngs[latlngs.length - 1] = new L.LatLng(v.lat, v.lon);
          layer.polyline.setLatLngs(latlngs);
        }
      }
    }
  } else {
    const marker = L.marker([v.lat, v.lon], { icon: shipIcon(color, heading, isPinned, isActive), title: v.name || mmsi });
    marker.on('click', () => selectVessel(mmsi));
    marker.bindPopup('', { maxWidth: 240, autoPan: false });
    marker.on('popupopen', () => {
      const d = state.vessels[mmsi]?.data;
      if (d) updatePopupContent(marker, d);
    });
    
    // Sync visibility with current filters before adding to map
    if (updateMarkerVisibility(marker, v)) {
      marker.addTo(map);
    }

    state.vessels[mmsi] = { marker, data: v, lastUpdate: Date.now() };
  }
}

export function updateVesselMarkerStyle(mmsi) {
  const v = state.vessels[mmsi];
  if (!v) return;
  const { color } = vesselTypeInfo(v.data.type, v.data.vtype_info);
  const heading = v.data.heading ?? v.data.cog ?? 0;
  const isPinned = state.selectedMmsis.has(mmsi);
  const isActive = (mmsi === state.activeMmsi);
  v.marker.setIcon(shipIcon(color, heading, isPinned, isActive));
}

function updateMarkerVisibility(marker, v) {
  const hideOthers = document.getElementById('hide-others')?.checked;
  const isPinned = state.selectedMmsis.has(v.mmsi);
  const isActive = (v.mmsi === state.activeMmsi);

  let visible = true;
  if (hideOthers) {
    // If "Hide Others" is ON, we only show pinned or active vessels.
    visible = isPinned || isActive;
  } else {
    // If "Hide Others" is OFF, we show vessels matching the search/category filter.
    const searchVal = document.getElementById('search')?.value.toLowerCase() || '';
    const catVal = document.getElementById('type-filter')?.value || 'all';
    
    let isMatch = true;
    const name = (v.name || '').toLowerCase();
    const mmsi = v.mmsi;

    if (searchVal && !name.includes(searchVal) && !mmsi.includes(searchVal)) {
      isMatch = false;
    }
    
    if (isMatch && catVal && catVal !== 'all') {
      const ti = vesselTypeInfo(v.type, v.vtype_info);
      if (ti.category !== catVal) isMatch = false;
    }
    
    visible = isMatch;
  }

  if (visible) {
    if (!map.hasLayer(marker)) marker.addTo(map);
    marker.setOpacity(1);
  } else {
    if (map.hasLayer(marker)) map.removeLayer(marker);
  }
  return visible;
}

export function syncMapMarkersVisibility() {
  for (const v of Object.values(state.vessels)) {
    updateMarkerVisibility(v.marker, v.data);
  }
}

export function updatePopupContent(marker, d) {
  const ti = vesselTypeInfo(d.type, d.vtype_info);
  marker.setPopupContent(`
    <div class="popup-title">${d.name || '(Unknown)'}</div>
    <div class="popup-row"><span>MMSI</span><span>${d.mmsi}</span></div>
    <div class="popup-row"><span>Type</span><span>${ti.label}</span></div>
    <div class="popup-row"><span>SOG</span><span>${d.sog != null ? d.sog.toFixed(1) + ' kn' : '—'}</span></div>
    <div class="popup-row"><span>COG</span><span>${d.cog != null ? d.cog.toFixed(0) + '°' : '—'}</span></div>
    <div class="popup-row"><span>Heading</span><span>${d.heading != null ? d.heading.toFixed(0) + '°' : '—'}</span></div>
    <div class="popup-row"><span>Dest</span><span>${d.destination || '—'}</span></div>
  `);
}

export function pruneStaleVessels(staleMinutes) {
  const cutoff = Date.now() - staleMinutes * 60 * 1000;
  for (const [mmsi, v] of Object.entries(state.vessels)) {
    if (v.lastUpdate < cutoff) {
      v.marker.setOpacity(0.3);
    }
  }
}
export function zoomToFitSelection() {
  const coords = [];
  
  // Add active vessel
  if (state.activeMmsi && state.vessels[state.activeMmsi]) {
    const v = state.vessels[state.activeMmsi].data;
    if (v.lat != null && v.lon != null) coords.push([v.lat, v.lon]);
  }
  
  // Add selected vessels
  state.selectedMmsis.forEach(mmsi => {
    if (mmsi !== state.activeMmsi && state.vessels[mmsi]) {
      const v = state.vessels[mmsi].data;
      if (v.lat != null && v.lon != null) coords.push([v.lat, v.lon]);
    }
  });

  if (coords.length === 0) return;

  if (coords.length === 1) {
    const targetZoom = Math.max(map.getZoom(), 12);
    // Standard centering logic for single ship (already exists in selectVessel but good here too)
    map.flyTo(coords[0], targetZoom, { animate: true, duration: 0.8 });
  } else {
    const bounds = L.latLngBounds(coords);
    const isMobile = window.innerWidth <= 768;
    
    // Correct Leaflet fitBounds padding: paddingTopLeft [left, top], paddingBottomRight [right, bottom]
    const paddingOptions = isMobile 
      ? { 
          paddingTopLeft: [70, 160],     // Left: toggle, Top: legend/controls
          paddingBottomRight: [140, Math.floor(window.innerHeight * 0.4)] // Right: legend width, Bottom: shelf
        }
      : { 
          paddingTopLeft: [360, 40],     // Left: sidebar, Top: buffer
          paddingBottomRight: [160, 200] // Right & Bottom: legend area
        };
    
    map.fitBounds(bounds, { ...paddingOptions, maxZoom: 15, animate: true, duration: 0.8 });
  }
}
