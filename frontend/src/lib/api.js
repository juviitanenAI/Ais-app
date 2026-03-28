import { currentSearchResults, vesselTypeCache, isBackendReady } from './stores.js';
import { API_BASE } from './config.js';

export async function waitForBackend() {
  while (true) {
    try {
      const res = await fetch(`${API_BASE}/up`, { method: 'HEAD' });
      if (res.ok) {
        isBackendReady.set(true);
        return;
      }
    } catch (e) {
      // Backend not reachable yet
    }
    await new Promise(resolve => setTimeout(resolve, 500));
  }
}

export async function fetchSearchResults(query = '', categories = []) {
  try {
    const params = new URLSearchParams();
    if (query) params.append('q', query);
    if (categories && categories.length > 0) {
      categories.forEach(cat => params.append('category', cat));
    }
    
    const qs = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/vessels${qs}`);
    if (res.ok) {
      currentSearchResults.set(await res.json());
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
  const data = await res.json();
  // Backend returns {"MMSI": [points...]}
  return data[mmsi] || [];
}

export async function fetchVesselTypes() {
  const res = await fetch(`${API_BASE}/api/vessel-types`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  vesselTypeCache.set(await res.json());
}

export async function fetchVesselCategories() {
  const res = await fetch(`${API_BASE}/api/vessel-categories`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
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

export async function fetchBuoys() {
  const res = await fetch(`${API_BASE}/api/buoys`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}
