import { API_BASE } from './config.js';
import { state } from './state.js';

export async function fetchSearchResults(query = '', category = '') {
  try {
    const params = new URLSearchParams();
    if (query) params.append('q', query);
    if (category) params.append('category', category);
    
    const qs = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/vessels${qs}`);
    if (res.ok) {
      state.currentSearchResults = await res.json();
    }
  } catch (e) {
    console.error('[search] Failed to fetch:', e);
  }
}

export async function fetchLiveVesselData() {
  const res = await fetch(`${API_BASE}/api/vessels/live`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchHistoryData(mmsi, minutes) {
  const res = await fetch(`${API_BASE}/api/history?mmsi=${encodeURIComponent(mmsi)}&minutes=${minutes}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchVesselTypes() {
  const res = await fetch(`${API_BASE}/api/vessel-types`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  state.vessel_type_cache = await res.json();
}

export async function fetchHeatmapData(minutes, category) {
  const params = new URLSearchParams({ minutes });
  if (category && category !== 'all') {
    params.append('category', category);
  }
  const res = await fetch(`${API_BASE}/api/heatmap?${params.toString()}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}
