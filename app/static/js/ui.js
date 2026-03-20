import { state } from './state.js';
import { vesselTypeInfo } from './utils.js';
import { clearHistory, renderHistory, clearSelectionRing, showSelectionRing, map, syncMapMarkersVisibility } from './map.js';
import { fetchHistoryData, fetchSearchResults } from './api.js';

export function scheduleListUpdate() {
  if (state.listUpdateTimer) return;
  state.listUpdateTimer = setTimeout(() => {
    state.listUpdateTimer = null;
    updateVesselCount();
    updateVesselList();
  }, 2000);
}

export function updateVesselCount() {
  document.getElementById('vessel-count').textContent = Object.keys(state.vessels).length;
}

export function updateVesselList(filter = null) {
  const listEl = document.getElementById('vessel-list');
  const searchVal = filter ?? document.getElementById('search').value.toLowerCase();

  const combined = new Map();
  for (const res of state.currentSearchResults) {
    combined.set(res.mmsi, { mmsi: res.mmsi, name: res.name, is_live: res.is_live, latest_ts: res.latest_ts });
  }

  const catVal = document.getElementById('type-filter').value;
  for (const [mmsi, v] of Object.entries(state.vessels)) {
    // Filter live vessels by category if filter is active
    if (catVal) {
      const liveCat = v.data.vtype_info?.category?.toLowerCase() || 'other';
      if (liveCat !== catVal) continue;
    }
    
    if (!combined.has(mmsi)) {
      combined.set(mmsi, { mmsi, name: v.data.name, is_live: true, latest_ts: Math.floor(v.lastUpdate / 1000) });
    } else {
      const item = combined.get(mmsi);
      item.is_live = true;
      item.latest_ts = Math.max(item.latest_ts || 0, Math.floor(v.lastUpdate / 1000));
    }
  }

  const sorted = Array.from(combined.values())
    .filter(v => {
      if (!searchVal) return true;
      return (v.name || '').toLowerCase().includes(searchVal) || v.mmsi.includes(searchVal);
    })
    .sort((a, b) => {
      const na = a.name || 'zzz';
      const nb = b.name || 'zzz';
      return na.localeCompare(nb);
    });

  const toRender = sorted.slice(0, 200);
  let html = '';
  for (const v of toRender) {
    const liveData = state.vessels[v.mmsi]?.data;
    const type = liveData ? liveData.type : null;
    const ti = vesselTypeInfo(type, liveData?.vtype_info);
    const isActive = v.mmsi === state.selectedMmsi;
    
    const speedStr = liveData && liveData.sog != null ? liveData.sog.toFixed(1) + ' kn' : '';
    const dotStyle = v.is_live ? `background:${ti.color}; box-shadow: 0 0 4px ${ti.color};` : `background:var(--text-muted); opacity:0.5;`;
    
    const latestDate = new Date(v.latest_ts * 1000);
    const timeStr = v.latest_ts > 0 ? latestDate.toLocaleString('fi-FI', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit'}) : 'Unknown';

    html += `<div class="vessel-item${isActive ? ' active' : ''}" data-mmsi="${v.mmsi}">
      <div class="vessel-dot" style="${dotStyle}"></div>
      <div class="vessel-info">
        <div class="vessel-name">${v.name || '(Unknown)'}</div>
        <div class="vessel-mmsi">${v.mmsi} <span style="font-size: 9px; color: var(--text-muted); margin-left: 6px;">Latest: ${timeStr}</span></div>
      </div>
      <div class="vessel-speed">${speedStr}</div>
    </div>`;
  }

  if (sorted.length > 200) html += `<div style="padding:10px 16px; font-size:11px; color:var(--text-muted);">Showing 200 of ${sorted.length} — refine search</div>`;
  if (!html) html = `<div style="padding:20px 16px; text-align:center; color:var(--text-muted); font-size:13px;">No vessels found</div>`;
  listEl.innerHTML = html;
  
  // Update legend dynamically if needed
  renderLegend();
}

let lastLegendSize = 0;
export function renderLegend() {
  const legendEl = document.getElementById('map-legend-items');
  if (!legendEl) return;

  // Group by category to keep legend lean
  const categories = {};
  for (const vtype of Object.values(state.vessel_type_cache)) {
    if (!vtype.category || vtype.category === 'other') continue;
    if (!categories[vtype.category]) {
      categories[vtype.category] = { color: vtype.color, label: vtype.category.charAt(0).toUpperCase() + vtype.category.slice(1) };
    }
  }
  
  const cats = Object.values(categories);
  if (cats.length === 0 && lastLegendSize === 0) {
    legendEl.innerHTML = '<div class="legend-row">No vessel types loaded</div>';
    return;
  }
  if (cats.length === lastLegendSize) return; 
  lastLegendSize = cats.length;

  let html = '';

  for (const cat of cats) {
    html += `<div class="legend-row"><div class="legend-dot" style="background:${cat.color}"></div> ${cat.label}</div>`;
  }
  // Always add Other
  html += `<div class="legend-row"><div class="legend-dot" style="background:var(--ship-other)"></div> Other</div>`;
  
  legendEl.innerHTML = html;
  populateTypeFilter(cats);
}

export function populateTypeFilter(categories) {
  const filterEl = document.getElementById('type-filter');
  if (!filterEl || filterEl.children.length > 1) return; // Already populated (except placeholder)

  for (const cat of categories) {
    const opt = document.createElement('option');
    opt.value = cat.label.toLowerCase();
    opt.textContent = cat.label;
    filterEl.appendChild(opt);
  }
  // Add Other
  const optOther = document.createElement('option');
  optOther.value = 'other';
  optOther.textContent = 'Other';
  filterEl.appendChild(optOther);
}

export function selectVessel(mmsi) {
  if (state.selectedMmsi !== mmsi) clearHistory();
  state.selectedMmsi = mmsi;

  document.querySelectorAll('.vessel-item').forEach(el => {
    el.classList.toggle('active', el.dataset.mmsi === mmsi);
  });

  const v = state.vessels[mmsi];
  if (v) {
    const targetZoom = Math.max(map.getZoom(), 10);
    const targetPoint = map.project([v.data.lat, v.data.lon], targetZoom);
    if (window.innerWidth <= 768) targetPoint.y += 150;
    else targetPoint.y -= 120;
    
    const adjustedCenter = map.unproject(targetPoint, targetZoom);
    map.flyTo(adjustedCenter, targetZoom, { animate: true, duration: 0.8 });
    if (window.innerWidth > 768) v.marker.openPopup();
    showSelectionRing([v.data.lat, v.data.lon]);
  }

  updateDetailPanel(mmsi);
  document.getElementById('detail-panel').classList.add('visible');
  document.getElementById('sidebar').classList.add('detail-view');

  document.getElementById('app').classList.add('sidebar-visible');
  document.getElementById('sidebar').classList.remove('collapsed');

  loadAndRenderHistory(mmsi);

  if (state.historyPollTimer) clearInterval(state.historyPollTimer);
  state.historyPollTimer = setInterval(() => {
    if (state.selectedMmsi) loadAndRenderHistory(state.selectedMmsi);
  }, 30000);
}

export async function loadAndRenderHistory(mmsi) {
  if (!mmsi) return;
  try {
    const data = await fetchHistoryData(mmsi, state.historyMinutes);
    if (mmsi !== state.selectedMmsi) return;
    const points = (data[mmsi] || []);
    renderHistory(mmsi, points);
  } catch (e) {
    console.error('[history] Failed:', e);
  }
}

export function updateDetailPanel(mmsi) {
  let name = '(Unknown)', typeLab = 'Unknown', typeCol = '#8899aa';
  let speed = '—', hdg = '—', cog = '—', dest = '—';

  const v = state.vessels[mmsi];
  if (v) {
    const d = v.data;
    const ti = vesselTypeInfo(d.type, d.vtype_info);
    name = d.name || name;
    typeLab = ti.label; typeCol = ti.color;
    speed = (d.sog != null) ? d.sog.toFixed(1) + ' kn' : speed;
    hdg = (d.heading != null) ? d.heading.toFixed(0) + '°' : hdg;
    cog = (d.cog != null) ? d.cog.toFixed(0) + '°' : cog;
    dest = d.destination || dest;
  } else {
    const match = state.currentSearchResults.find(r => r.mmsi === mmsi);
    if (match) name = match.name || name;
  }

  document.getElementById('detail-name').textContent = name;
  document.getElementById('detail-grid').innerHTML = `
    <div class="detail-field"><div class="detail-label">MMSI</div><div class="detail-value">${mmsi}</div></div>
    <div class="detail-field"><div class="detail-label">Type</div><div class="detail-value" style="color:${typeCol}">${typeLab}</div></div>
    <div class="detail-field"><div class="detail-label">Speed</div><div class="detail-value">${speed}</div></div>
    <div class="detail-field"><div class="detail-label">Heading</div><div class="detail-value">${hdg}</div></div>
    <div class="detail-field"><div class="detail-label">Course</div><div class="detail-value">${cog}</div></div>
    <div class="detail-field"><div class="detail-label">Destination</div><div class="detail-value">${dest}</div></div>
  `;
}

export function initUIListeners() {
  document.getElementById('vessel-list').addEventListener('click', (e) => {
    const item = e.target.closest('.vessel-item');
    if (!item) return;
    selectVessel(item.dataset.mmsi);
  });

  let searchTimer = null;
  document.getElementById('search').addEventListener('input', (e) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      const query = document.getElementById('search').value.trim();
      const category = document.getElementById('type-filter').value;
      fetchSearchResults(query, category).then(() => {
        updateVesselList();
        syncMapMarkersVisibility();
        if (query !== '' || category !== '') {
          document.getElementById('app').classList.add('sidebar-visible');
          document.getElementById('sidebar').classList.remove('collapsed');
        }
      });
    }, 250);
  });

  document.getElementById('type-filter').addEventListener('change', () => {
    const query = document.getElementById('search').value.trim();
    const category = document.getElementById('type-filter').value;
    fetchSearchResults(query, category).then(() => {
      updateVesselList();
      syncMapMarkersVisibility();
    });
  });

  document.getElementById('search').addEventListener('focus', () => {
    if (window.innerWidth <= 768) {
      document.getElementById('app').classList.add('sidebar-visible');
      document.getElementById('sidebar').classList.remove('collapsed');
    }
  });

  document.getElementById('detail-close').addEventListener('click', () => {
    state.selectedMmsi = null;
    if (state.historyPollTimer) {
      clearInterval(state.historyPollTimer);
      state.historyPollTimer = null;
    }
    document.getElementById('detail-panel').classList.remove('visible');
    document.getElementById('sidebar').classList.remove('detail-view');
    clearHistory();
    clearSelectionRing();
    document.querySelectorAll('.vessel-item.active').forEach(el => el.classList.remove('active'));
  });

  document.querySelectorAll('.history-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.history-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.historyMinutes = parseInt(btn.dataset.minutes);
      if (state.selectedMmsi) loadAndRenderHistory(state.selectedMmsi);
    });
  });

  document.getElementById('sidebar-toggle').addEventListener('click', () => {
    const app = document.getElementById('app');
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');
    app.classList.toggle('sidebar-visible');
    setTimeout(() => map.invalidateSize(), 350);
  });

  document.getElementById('mobile-list-close').addEventListener('click', () => {
    document.getElementById('sidebar').classList.add('collapsed');
    document.getElementById('app').classList.remove('sidebar-visible');
    setTimeout(() => map.invalidateSize(), 350);
  });
}
