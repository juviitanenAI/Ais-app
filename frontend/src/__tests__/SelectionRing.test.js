import { describe, it, expect, vi, beforeEach } from 'vitest';
import { vessels, activeMmsi, activeBuoySite, selectedMmsis } from '../lib/stores.js';
import * as mapLib from '../lib/map.js';

// Mock L and other dependencies (reuse from existing tests if possible, but let's define what we need here)
global.L = {
  latLngBounds: vi.fn((pts) => ({
    pts,
    isValid: () => pts && pts.length > 0,
    getNorthEast: () => ({ equals: () => true }),
    getSouthWest: () => ({ equals: () => true })
  })),
  polyline: vi.fn(() => ({
    addTo: vi.fn().mockReturnThis(),
    getLatLngs: vi.fn(() => []),
    setLatLngs: vi.fn().mockReturnThis()
  })),
  marker: vi.fn(function() {
    const m = {
      addTo: vi.fn(function(mapObj) {
        if (mapObj && mapObj.addLayer) mapObj.addLayer(m);
        return m;
      }),
      on: vi.fn().mockReturnThis(),
      bindPopup: vi.fn().mockReturnThis(),
      setLatLng: vi.fn().mockReturnThis(),
      setIcon: vi.fn().mockReturnThis(),
      setZIndexOffset: vi.fn().mockReturnThis(),
      getLatLng: vi.fn(() => ({ lat: 0, lng: 0 })),
      getPopup: vi.fn(),
      isPopupOpen: vi.fn()
    };
    return m;
  }),
  map: vi.fn(() => ({
    setView: vi.fn().mockReturnThis(),
    fitBounds: vi.fn().mockReturnThis(),
    invalidateSize: vi.fn().mockReturnThis(),
    removeLayer: vi.fn().mockReturnThis(),
    addLayer: vi.fn().mockReturnThis(),
    on: vi.fn().mockReturnThis(),
    getZoom: vi.fn().mockReturnValue(10)
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
  LatLng: vi.fn(function(lat, lon) { return { lat, lon }; })
};

describe('Selection Ring Logic', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vessels.set({});
    activeMmsi.set(null);
    activeBuoySite.set(null);
    selectedMmsis.set(new Set());
    
    // Reset mapLib internal state
    mapLib.initMap(document.createElement('div'));
    mapLib.buoyMarkers.clear();
  });

  it('shows selection ring when a vessel is active', () => {
    const mockMarker = L.marker();
    vessels.set({
      '123': { marker: mockMarker, data: { mmsi: '123', lat: 60, lon: 24 } }
    });
    
    mapLib.updateHighlights('123', new Set());
    
    // Check if a marker was added (the selection ring is a marker with divIcon)
    // In our implementation, showSelectionRing adds a marker to the map.
    expect(mapLib.map.addLayer).toHaveBeenCalled();
  });

  it('shows selection ring when a buoy is active', () => {
    const mockMarker = L.marker();
    mapLib.buoyMarkers.set(456, mockMarker);
    
    mapLib.updateHighlights(null, new Set(), 456);
    
    expect(mapLib.map.addLayer).toHaveBeenCalled();
    expect(mockMarker.setIcon).toHaveBeenCalled();
  });

  it('clears selection ring when nothing is active', () => {
    // First show it
    mapLib.showSelectionRing([60, 24]);
    expect(mapLib.selectionRing).not.toBeNull();
    
    // Then update with nulls
    mapLib.updateHighlights(null, new Set(), null);
    
    expect(mapLib.map.removeLayer).toHaveBeenCalled();
    expect(mapLib.selectionRing).toBeNull();
  });

  it('clears selection ring when isHeatmap is true', () => {
    const mockMarker = L.marker();
    vessels.set({
      '123': { marker: mockMarker, data: { mmsi: '123', lat: 60, lon: 24 } }
    });
    
    // First show it in normal mode
    mapLib.updateHighlights('123', new Set(), null, false);
    expect(mapLib.selectionRing).not.toBeNull();
    
    // Then update with isHeatmap = true
    mapLib.updateHighlights('123', new Set(), null, true);
    
    expect(mapLib.map.removeLayer).toHaveBeenCalled();
    expect(mapLib.selectionRing).toBeNull();
  });
});
