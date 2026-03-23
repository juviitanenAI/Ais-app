import { describe, it, expect, vi, beforeEach } from 'vitest';
import { vessels, activeMmsi, autoFollow } from '../lib/stores.js';
import { get } from 'svelte/store';
import * as mapLib from '../lib/map.js';

// Minimal Leaflet mock
global.L = {
  latLngBounds: vi.fn((pts) => ({
    pts,
    isValid: () => pts && pts.length > 0
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
  LatLng: vi.fn(function(lat, lon) { return { lat, lon }; })
};

describe('Map Logic', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vessels.set({});
    autoFollow.set(true); // Default to true for existing tests
    mapLib.clearHistory();
    // Re-init map for testing
    const el = document.createElement('div');
    mapLib.initMap(el);
  });

  it('fitToVessels collects live coordinates', () => {
    vessels.set({
      '123': { data: { mmsi: 123, lat: 60.1, lon: 24.9 } }
    });

    mapLib.fitToVessels([123]);

    expect(global.L.latLngBounds).toHaveBeenCalledWith([
      [60.1, 24.9]
    ]);
    expect(mapLib.map.fitBounds).toHaveBeenCalled();
  });

  it('fitToVessels includes history coordinates if available', () => {
    vessels.set({
      '123': { data: { mmsi: 123, lat: 60.1, lon: 24.9 } }
    });

    // Mock history layer
    const mockPolyline = {
      getLatLngs: () => [[60.0, 24.8], [59.9, 24.7]]
    };
    mapLib.historyLayers.set(123, { polyline: mockPolyline });
    autoFollow.set(false); // history is only included when autoFollow is false

    mapLib.fitToVessels([123]);

    const expectedPoints = [
      [60.1, 24.9],
      [60.0, 24.8],
      [59.9, 24.7]
    ];
    expect(global.L.latLngBounds).toHaveBeenCalledWith(expectedPoints);
  });

  it('fitToVessels handles multiple vessels', () => {
    vessels.set({
      '123': { data: { mmsi: 123, lat: 60.1, lon: 24.9 } },
      '456': { data: { mmsi: 456, lat: 61.1, lon: 25.9 } }
    });

    mapLib.fitToVessels([123, 456]);

    const expectedPoints = [
      [60.1, 24.9],
      [61.1, 25.9]
    ];
    expect(global.L.latLngBounds).toHaveBeenCalledWith(expectedPoints);
  });

  it('addOrUpdateVessel triggers fitToVessels for active vessel', () => {
    const v = { mmsi: 123, lat: 60.1, lon: 24.9 };
    activeMmsi.set(123);
    
    // First call to addOrUpdateVessel (new vessel)
    mapLib.addOrUpdateVessel(v, vi.fn());
    
    // It should NOT call fitToVessels on new vessel creation? 
    // Wait, my code calls it if mmsi === activeMmsi.
    // Let's check.
    
    expect(mapLib.map.fitBounds).toHaveBeenCalled();
  });

  it('does NOT reset autoFollow on map drag or zoom (removed feature)', () => {
    autoFollow.set(true);
    
    // Check that dragstart is NOT registered
    const dragHandlerCall = mapLib.map.on.mock.calls.find(call => call[0] === 'dragstart');
    expect(dragHandlerCall).toBeUndefined();

    // Check that zoomstart is also NOT registered
    const zoomHandlerCall = mapLib.map.on.mock.calls.find(call => call[0].includes('zoomstart'));
    expect(zoomHandlerCall).toBeUndefined();
  });
});
