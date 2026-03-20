import { API_BASE } from './config.js';
import { state } from './state.js';

export async function fetchSearchResults(query = '') {
  try {
    const q = query ? `?q=${encodeURIComponent(query)}` : '';
    const res = await fetch(`${API_BASE}/api/vessels${q}`);
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
