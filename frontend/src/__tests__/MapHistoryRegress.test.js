import { describe, it, expect, vi, beforeEach } from 'vitest';
import { filterCategories, heatmapMode, activeMmsi, selectedMmsis } from '../lib/stores.js';
import * as mapLib from '../lib/map.js';

// Minimal Leaflet mock
global.L = {
  latLngBounds: vi.fn((pts) => ({
    pts,
    isValid: () => pts && pts.length > 0,
    getNorthEast: () => ({ equals: (other) => true }),
    getSouthWest: () => ({ equals: (other) => true })
  })),
  polyline: vi.fn(() => ({
    addTo: vi.fn().mockReturnThis(),
    getLatLngs: vi.fn(() => []),
    setLatLngs: vi.fn().mockReturnThis()
  })),
  marker: vi.fn(() => ({
    addTo: vi.fn().mockReturnThis(),
    on: vi.fn().mockReturnThis(),
    bindPopup: vi.fn().mockReturnThis(),
    setLatLng: vi.fn().mockReturnThis(),
    setIcon: vi.fn().mockReturnThis(),
    setOpacity: vi.fn().mockReturnThis(),
    getPopup: vi.fn(),
    isPopupOpen: vi.fn()
  })),
  map: vi.fn(() => ({
    setView: vi.fn().mockReturnThis(),
    fitBounds: vi.fn().mockReturnThis(),
    invalidateSize: vi.fn().mockReturnThis(),
    removeLayer: vi.fn().mockReturnThis(),
    addLayer: vi.fn().mockReturnThis(),
    hasLayer: vi.fn().mockReturnValue(true),
    on: vi.fn().mockReturnThis(),
    getZoom: vi.fn().mockReturnValue(18),
    getCenter: vi.fn().mockReturnValue({ lat: 60, lng: 24 })
  })),
  tileLayer: vi.fn(() => ({
    addTo: vi.fn().mockReturnThis()
  })),
  control: {
    layers: vi.fn(() => ({
      addTo: vi.fn().mockReturnThis()
    }))
  },
  latLng: vi.fn((lat, lon) => ({ lat, lon })),
  divIcon: vi.fn((options) => options),
  LatLng: vi.fn(function(lat, lon) { return { lat, lon }; }),
  heatLayer: vi.fn(() => ({
    addTo: vi.fn().mockReturnThis()
  }))
};

describe('History Trail Persistence', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    filterCategories.set([]);
    heatmapMode.set(false);
    activeMmsi.set(null);
    selectedMmsis.set(new Set());
    mapLib.clearHistory();
    const el = document.createElement('div');
    mapLib.initMap(el);
  });

  it('clearHeatmap() only clears heatmap, not history trails (the fix)', () => {
    // 1. Add a history layer
    const mockPolyline = { addTo: vi.fn(), remove: vi.fn() };
    mapLib.historyLayers.set('123', { polyline: mockPolyline, circles: [] });
    
    // 2. Add a heatmap layer using the real function
    mapLib.renderHeatmap([[60, 24, 1]]);

    // 3. Call clearHeatmap
    mapLib.clearHeatmap();

    // Verify heatmap is null, but history still exists
    expect(mapLib.heatmapLayer).toBeNull();
    expect(mapLib.historyLayers.size).toBe(1);
    expect(mapLib.historyLayers.has('123')).toBe(true);
  });

  it('clearHistory() only clears history, not heatmap', () => {
    const mockPolyline = { addTo: vi.fn(), remove: vi.fn() };
    mapLib.historyLayers.set('123', { polyline: mockPolyline, circles: [] });
    mapLib.renderHeatmap([[60, 24, 1]]);

    mapLib.clearHistory();

    expect(mapLib.historyLayers.size).toBe(0);
    expect(mapLib.heatmapLayer).not.toBeNull();
  });
});
