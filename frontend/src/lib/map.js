import { get } from 'svelte/store';
import { vessels as vesselsStore, buoys as buoysStore, activeBuoySite, selectedMmsis, activeMmsi, heatmapMode, filterCategories, hideOthers, sidebarCollapsed, autoFollow } from './stores.js';
import { vesselTypeInfo, shipIcon, buoyIcon } from './utils.js';

export let map = null;
export let heatmapLayer = null;
export let selectionRing = null;
export let historyLayers = new Map();
export let buoyMarkers = new Map();

export function initMap(element) {
  map = L.map(element, {
    zoomControl: false,
    attributionControl: true,
    preferCanvas: true,
  }).setView([60.5, 22.0], 7);

  const voyager = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
  });

  const darkMatter = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
  });

  const osmStandard = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  });

  voyager.addTo(map);

  const baseLayers = {
    "Voyager (Clean)": voyager,
    "Dark Matter (Night)": darkMatter,
    "Standard (OSM)": osmStandard
  };

  L.control.layers(baseLayers, {}, { position: 'topright' }).addTo(map);
  
  // REMOVED: No auto-reset on drag/zoom, as user wants persistence until explicit close/declick

  return map;
}

export function setAutoFollow(enabled) {
  autoFollow.set(enabled);
  if (enabled) {
    const active = get(activeMmsi);
    if (active) {
      fitToVessels([String(active)], true, 18);
    }
  }
}

export function clearSelectionRing() {
  if (selectionRing) {
    map.removeLayer(selectionRing);
    selectionRing = null;
  }
}

export function showSelectionRing(latlng) {
  clearSelectionRing();
  selectionRing = L.marker(latlng, {
    icon: L.divIcon({ className: '', html: '<div class="selected-ring"></div>', iconSize: [48, 48], iconAnchor: [24, 24] }),
    interactive: false,
    zIndexOffset: -1,
  }).addTo(map);
}

export function clearHistory(mmsi = null) {
  if (heatmapLayer) {
    map.removeLayer(heatmapLayer);
    heatmapLayer = null;
  }

  if (mmsi) {
    const layer = historyLayers.get(mmsi);
    if (layer) {
      map.removeLayer(layer.polyline);
      (layer.circles || []).forEach(c => map.removeLayer(c));
      historyLayers.delete(mmsi);
    }
  } else {
    historyLayers.forEach((layer) => {
      map.removeLayer(layer.polyline);
      (layer.circles || []).forEach(c => map.removeLayer(c));
    });
    historyLayers.clear();
  }
}

export function renderHeatmap(points, color = null) {
  if (heatmapLayer) {
    map.removeLayer(heatmapLayer);
    heatmapLayer = null;
  }
  if (!points || !points.length) return;
  
  let maxWeight = Math.max(1, ...points.map(p => p[2]));
  let gradient = { 0.4: 'blue', 0.65: 'lime', 1: 'red' }; 
  if (color) {
    gradient = {
      0.2: color + '22',
      0.4: color + '44',
      0.5: color + '88',
      0.65: color + 'bb',
      0.9: color,
      1.0: '#ffffff'
    };
  }

  heatmapLayer = L.heatLayer(points, {
    radius: 15,
    blur: 18,
    maxZoom: 10,
    max: Math.max(1, maxWeight * 0.4),
    gradient: gradient
  }).addTo(map);
}

export function renderHistory(mmsi, points) {
  clearHistory(mmsi);
  console.log(`[map] renderHistory for ${mmsi}, points:`, points.length);
  
  const vessels = get(vesselsStore);
  const liveData = vessels[mmsi]?.data;
  const coords = points.map(p => [p.lat, p.lon]);
  
  if (liveData && liveData.lat != null && liveData.lon != null) {
    coords.push([liveData.lat, liveData.lon]);
  }

  if (coords.length < 2) {
    console.warn(`[map] Not enough points for trail ${mmsi}:`, coords.length);
    return;
  }

  const { color } = vesselTypeInfo(liveData?.type, liveData?.vtype_info);
  const isActive = (mmsi == get(activeMmsi));
  
  const polyline = L.polyline(coords, {
    color,
    weight: isActive ? 5 : 3,
    opacity: isActive ? 0.9 : 0.6,
    dashArray: isActive ? null : '6, 6',
    lineJoin: 'round',
    smoothFactor: 1.0
  });

  if (map) {
    polyline.addTo(map);
    console.log(`[map] Added trail for ${mmsi} to map with ${coords.length} points`);
  } else {
    console.error(`[map] Cannot add trail for ${mmsi}, map is null`);
  }

  const circles = [];
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

  historyLayers.set(mmsi, { polyline, circles });
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

export function updateMarkerVisibility(marker, vesselData) {
  if (!marker || !vesselData || !map) return;
  
  const hMode = get(heatmapMode);
  const fCats = get(filterCategories);
  const hOthers = get(hideOthers);
  
  const mmsi = vesselData.mmsi;
  const isSelected = get(selectedMmsis).has(mmsi) || mmsi == get(activeMmsi);
  
  const matchesFilter = isSelected || fCats.length === 0 || fCats.includes(vesselData.vtype_info?.category?.toLowerCase());
  const matchesHideOthers = isSelected || !hOthers;

  if (hMode || !matchesFilter || !matchesHideOthers) {
    if (map.hasLayer(marker)) map.removeLayer(marker);
  } else {
    if (!map.hasLayer(marker)) marker.addTo(map);
  }
}

export function updateHighlights(activeMmsiId, selectedMmsisSet, activeBuoyId = null) {
  if (!map) return;
  const vs = get(vesselsStore);
  
  Object.entries(vs).forEach(([mmsi, v]) => {
    const isPinned = selectedMmsisSet.has(mmsi);
    const isActive = (mmsi == activeMmsiId);
    const { color } = vesselTypeInfo(v.data.type, v.data.vtype_info);
    const heading = v.data.heading ?? v.data.cog ?? 0;
    
    v.marker.setIcon(shipIcon(color, heading, isPinned, isActive));
    if (isActive) {
      v.marker.setZIndexOffset(1000);
      showSelectionRing([v.data.lat, v.data.lon]);
    } else {
      v.marker.setZIndexOffset(0);
    }
  });

  // Update buoys
  buoyMarkers.forEach((marker, siteNum) => {
    const isActive = (siteNum === activeBuoyId);
    marker.setIcon(buoyIcon(isActive));
    if (isActive) {
      marker.setZIndexOffset(1000);
      showSelectionRing(marker.getLatLng());
    } else if (!activeMmsiId) {
       // Only lower z-index if no vessel is active too
       marker.setZIndexOffset(-50);
    }
  });

  if (!activeMmsiId && !activeBuoyId) {
    clearSelectionRing();
  }
}

export function addOrUpdateVessel(v, onSelectCallback) {
  if (!map) return;
  const vessels = get(vesselsStore);
  const mmsi = v.mmsi;
  const { color } = vesselTypeInfo(v.type, v.vtype_info);
  const heading = v.heading ?? v.cog ?? 0;
  
  const selected = get(selectedMmsis);
  const isPinned = selected.has(mmsi);
  const isActive = (mmsi == get(activeMmsi));

  if (vessels[mmsi]) {
    const existing = vessels[mmsi];
    existing.data = v;
    existing.lastUpdate = Date.now();
    existing.marker.setLatLng([v.lat, v.lon]);
    existing.marker.setIcon(shipIcon(color, heading, isPinned, isActive));
    existing.marker.setOpacity(1);
    
    if (existing.marker.getPopup() && existing.marker.isPopupOpen()) {
      updatePopupContent(existing.marker, v);
    }

    if (mmsi === get(activeMmsi) || selected.has(mmsi)) {
      if (mmsi === get(activeMmsi) && selectionRing) {
        selectionRing.setLatLng([v.lat, v.lon]);
      }
      const layer = historyLayers.get(mmsi);
      if (layer) {
        const latlngs = layer.polyline.getLatLngs();
        if (latlngs && latlngs.length > 0) {
          latlngs[latlngs.length - 1] = new L.LatLng(v.lat, v.lon);
          layer.polyline.setLatLngs(latlngs);
        }
      }
      
      // Auto-pan/follow: adjust bounds to keep tracked vessels and tails in view
      const active = get(activeMmsi);
      const selectedList = Array.from(get(selectedMmsis));
      const allToTrack = [active, ...selectedList].filter(Boolean).map(String);
      fitToVessels(allToTrack, false);
    }
  } else {
    const marker = L.marker([v.lat, v.lon], { icon: shipIcon(color, heading, isPinned, isActive), title: v.name || mmsi });
    marker.on('click', () => onSelectCallback(mmsi));
    marker.bindPopup('', { maxWidth: 240, autoPan: false });
    marker.on('popupopen', () => {
      const d = get(vesselsStore)[mmsi]?.data;
      if (d) updatePopupContent(marker, d);
    });
    
    marker.addTo(map);
    
    vesselsStore.update(vs => {
      vs[mmsi] = { marker, data: v, lastUpdate: Date.now() };
      return { ...vs };
    });
 
    if (isPinned || isActive) {
      const active = get(activeMmsi);
      const selectedList = Array.from(get(selectedMmsis));
      const allToTrack = [active, ...selectedList].filter(Boolean).map(String);
      fitToVessels(allToTrack, false);
    }
  }
}

export function focusOnBounds(bounds, force = true, maxZoom = 18) {
  if (!map || !bounds) return;

  const isMobile = window.innerWidth <= 768;
  const isSidebarVisible = !get(sidebarCollapsed);
  const hasActive = !!get(activeMmsi) || !!get(activeBuoySite);

  let options = { maxZoom: maxZoom, animate: force };

  if (isMobile && isSidebarVisible) {
    // On mobile, the sidebar/detail panel at the bottom obscures the map.
    // Use a more moderate bottom padding.
    const bottomPadding = hasActive ? Math.min(window.innerHeight * 0.55, 450) : window.innerHeight * 0.35;
    options.paddingTopLeft = [10, 20];
    options.paddingBottomRight = [10, bottomPadding];
  } else if (!isMobile && isSidebarVisible) {
    // On desktop, the sidebar is on the left (340px)
    options.paddingTopLeft = [360, 40];
    options.paddingBottomRight = [40, 40];
  } else {
    options.padding = [40, 40];
  }

  map.invalidateSize();
  
  // For background updates of a single point, we want to preserve zoom but respect padding.
  if (!force && bounds.getNorthEast().equals(bounds.getSouthWest())) {
    options.maxZoom = map.getZoom();
  }
  
  map.fitBounds(bounds, options);
}

export function fitToVessels(mmsis, force = true, maxZoom = 18) {
  if (!map || !mmsis || mmsis.length === 0) return;
  const following = get(autoFollow);
  
  console.log(`[map] fitToVessels for ${mmsis.join(',')}, force=${force}, zoom=${maxZoom}, autoFollow=${following}`);

  if (!force && !following) return;

  const latlngs = [];
  const vessels = get(vesselsStore);

  mmsis.forEach(mmsi => {
    // Current position
    const v = vessels[mmsi]?.data;
    if (v && v.lat != null && v.lon != null && v.lat !== 0) {
      latlngs.push([v.lat, v.lon]);
    }

    // History points
    if (!get(autoFollow)) {
      const layer = historyLayers.get(mmsi);
      if (layer && layer.polyline) {
        const points = layer.polyline.getLatLngs();
        if (Array.isArray(points)) {
          points.forEach(p => {
            if (p && p.lat !== 0) latlngs.push(p);
          });
        }
      }
    }
  });

  if (latlngs.length > 0) {
    const bounds = L.latLngBounds(latlngs);
    focusOnBounds(bounds, force, maxZoom);
  }
}

export function addOrUpdateBuoy(b) {
  if (!map) return;
  const siteNum = b.data.siteNumber;
  const isActive = (siteNum === get(activeBuoySite));
  
  if (buoyMarkers.has(siteNum)) {
    const marker = buoyMarkers.get(siteNum);
    marker.setLatLng([b.lat, b.lon]);
    marker.setIcon(buoyIcon(isActive));
    if (marker.getPopup() && marker.isPopupOpen()) {
      updateBuoyPopupContent(marker, b.data);
    }
  } else {
    const marker = L.marker([b.lat, b.lon], { 
      icon: buoyIcon(isActive), 
      title: b.data.siteName || String(siteNum),
      zIndexOffset: -50 // Buoys below vessels
    });
    
    marker.on('click', () => {
      activeBuoySite.set(siteNum);
      activeMmsi.set(null); // Clear vessel selection when clicking buoy
    });
    
    marker.bindPopup('', { maxWidth: 240, autoPan: false });
    marker.on('popupopen', () => {
      updateBuoyPopupContent(marker, b.data);
    });
    
    marker.addTo(map);
    buoyMarkers.set(siteNum, marker);
  }
  updateBuoyVisibility(buoyMarkers.get(siteNum));
}

export function updateBuoyPopupContent(marker, d) {
  marker.setPopupContent(`
    <div class="popup-title">${d.siteName || '(Unknown Site)'}</div>
    <div class="popup-row"><span>Site #</span><span>${d.siteNumber}</span></div>
    <div class="popup-row"><span>Type</span><span>${d.siteType}</span></div>
    ${d.temperature !== null ? `<div class="popup-row"><span>Temp</span><span>${d.temperature}°C</span></div>` : ''}
    ${d.seaState ? `<div class="popup-row"><span>Sea State</span><span>${d.seaState}</span></div>` : ''}
    <div class="popup-footer">Last Update: ${new Date(d.lastUpdate).toLocaleString()}</div>
  `);
}

export function updateBuoyVisibility(marker) {
  if (!marker || !map) return;
  const hMode = get(heatmapMode);
  if (hMode) {
    if (map.hasLayer(marker)) map.removeLayer(marker);
  } else {
    if (!map.hasLayer(marker)) marker.addTo(map);
  }
}

export function focusOnBuoy(buoy) {
  if (!map || !buoy) return;
  const bounds = L.latLngBounds([[buoy.lat, buoy.lon]]);
  focusOnBounds(bounds, true, 15);
  const marker = buoyMarkers.get(buoy.data.siteNumber);
  if (marker) {
    marker.openPopup();
  }
}
