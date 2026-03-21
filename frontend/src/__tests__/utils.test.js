import { describe, it, expect, beforeEach } from 'vitest';
import { vesselTypeInfo, createShipSvg, compareVessels, filterVessels } from '../lib/utils.js';
import { vesselTypeCache } from '../lib/stores.js';

describe('Utility Functions', () => {
  beforeEach(() => {
    vesselTypeCache.set({});
  });

  describe('vesselTypeInfo', () => {
    it('returns provided info if valid', () => {
      const info = { label: 'Custom', color: '#fff', category: 'custom' };
      expect(vesselTypeInfo(null, info)).toEqual(info);
    });

    it('returns unknown for null typeCode and no info', () => {
      expect(vesselTypeInfo(null)).toEqual({ label: 'Unknown', color: '#8899aa', category: 'other' });
    });

    it('maps Cargo types correctly', () => {
      expect(vesselTypeInfo(70)).toEqual({ label: 'Cargo', color: '#4a9eff', category: 'cargo' });
      expect(vesselTypeInfo(79)).toEqual({ label: 'Cargo', color: '#4a9eff', category: 'cargo' });
    });

    it('maps Tanker types correctly', () => {
      expect(vesselTypeInfo(80)).toEqual({ label: 'Tanker', color: '#ff6b6b', category: 'tanker' });
    });

    it('uses cache if available', () => {
      vesselTypeCache.set({
        '100': { desc_en: 'Special', color: '#000', category: 'special' }
      });
      expect(vesselTypeInfo(100)).toEqual({ label: 'Special', color: '#000', category: 'special' });
    });
  });

  describe('createShipSvg', () => {
    it('generates svg with correct color and rotation', () => {
      const svg = createShipSvg('#ff0000', 90);
      expect(svg).toContain('fill="#ff0000"');
      expect(svg).toContain('transform:rotate(90deg)');
    });

    it('adds pinned class if isPinned is true', () => {
      const svg = createShipSvg('#fff', 0, true);
      expect(svg).toContain('ship-icon pinned');
    });

    it('adds active class if isActive is true', () => {
      const svg = createShipSvg('#fff', 0, false, true);
      expect(svg).toContain('ship-icon active');
      expect(svg).toContain('scale(1.2)');
    });
  });

  describe('compareVessels', () => {
    it('sorts selected vessels to the top', () => {
      const a = { mmsi: '1', name: 'A' };
      const b = { mmsi: '2', name: 'B' };
      const selected = new Set(['2']);
      
      expect(compareVessels(a, b, selected, null)).toBe(1); // B is first
    });

    it('sorts by name same selection state', () => {
      const a = { mmsi: '1', name: 'B' };
      const b = { mmsi: '2', name: 'A' };
      const selected = new Set();
      
      expect(compareVessels(a, b, selected, null)).toBe(1); // A (b) comes before B (a)
    });
  });

  describe('filterVessels', () => {
    const vessels = [
      { mmsi: 123, name: 'Ship A' },
      { mmsi: 456, name: 'Boat B' }
    ];

    it('returns all when query is empty', () => {
      expect(filterVessels(vessels, '')).toEqual(vessels);
    });

    it('filters by name', () => {
      expect(filterVessels(vessels, 'ship')).toEqual([vessels[0]]);
    });

    it('filters by mmsi', () => {
      expect(filterVessels(vessels, '456')).toEqual([vessels[1]]);
    });
  });
});
