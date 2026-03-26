import { describe, it, expect, vi, beforeEach } from 'vitest';
import { activeMmsi, sidebarCollapsed, activeBuoySite } from '../lib/stores.js';
import * as mapLib from '../lib/map.js';

// Reuse L mock from SelectionRing if needed, or define here
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
  marker: vi.fn(() => ({
    addTo: vi.fn().mockReturnThis(),
    on: vi.fn().mockReturnThis(),
    bindPopup: vi.fn().mockReturnThis(),
    setLatLng: vi.fn().mockReturnThis(),
    setIcon: vi.fn().mockReturnThis(),
    setZIndexOffset: vi.fn().mockReturnThis(),
    getLatLng: vi.fn(() => ({ lat: 60, lng: 24 })),
    getPopup: vi.fn(),
    isPopupOpen: vi.fn()
  })),
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

describe('Map Focus Logic', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    activeMmsi.set(null);
    activeBuoySite.set(null);
    sidebarCollapsed.set(false);
    
    // Reset mapLib internal state
    mapLib.initMap(document.createElement('div'));
    
    // Global mocks for window
    global.innerWidth = 800;
    global.innerHeight = 600;
  });

  it('uses mobile padding when window.innerWidth <= 768 and sidebar is visible', () => {
    global.innerWidth = 375;
    global.innerHeight = 667;
    activeMmsi.set('123'); // So hasActive is true
    
    const bounds = L.latLngBounds([[60, 24]]);
    mapLib.focusOnBounds(bounds);
    
    expect(mapLib.map.fitBounds).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({
            paddingTopLeft: expect.arrayContaining([10, 20]),
            paddingBottomRight: expect.arrayContaining([10, expect.any(Number)])
        })
    );
  });

  it('uses desktop padding when window.innerWidth > 768 and sidebar is visible', () => {
    global.innerWidth = 1200;
    global.innerHeight = 800;
    
    const bounds = L.latLngBounds([[60, 24]]);
    mapLib.focusOnBounds(bounds);
    
    expect(mapLib.map.fitBounds).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({
            paddingTopLeft: expect.arrayContaining([360, 40]),
            paddingBottomRight: expect.arrayContaining([40, 40])
        })
    );
  });

  it('uses simple padding when sidebar is collapsed', () => {
    sidebarCollapsed.set(true);
    
    const bounds = L.latLngBounds([[60, 24]]);
    mapLib.focusOnBounds(bounds);
    
    expect(mapLib.map.fitBounds).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({
            padding: expect.arrayContaining([40, 40])
        })
    );
  });
});
