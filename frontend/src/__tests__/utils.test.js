import { describe, it, expect, beforeEach } from 'vitest';
import { vesselTypeInfo, createShipSvg, compareVessels, filterVessels, formatDate } from '../lib/utils.js';
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

    it('maps Cargo types using cache', () => {
      vesselTypeCache.set({ '70': { category: 'cargo', color: '#4a9eff', desc_en: 'Cargo' } });
      expect(vesselTypeInfo(70)).toEqual({ label: 'Cargo', color: '#4a9eff', category: 'cargo' });
    });

    it('maps Tanker types using cache', () => {
      vesselTypeCache.set({ '80': { category: 'tanker', color: '#ff6b6b', desc_en: 'Tanker' } });
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

  describe('formatDate', () => {
    it('formats unix timestamp in seconds correctly', () => {
      // 1711561511 -> 27.03.2024
      const result = formatDate(1711561511);
      expect(result).toMatch(/27\.03\.2024.*?19[:.]45/);
    });

    it('formats unix timestamp in milliseconds correctly', () => {
      const result = formatDate(1711561511000);
      expect(result).toMatch(/27\.03\.2024.*?19[:.]45/);
    });

    it('formats ISO string correctly', () => {
      const result = formatDate("2024-03-27T19:45:00Z");
      // Environment timezone might affect the hours, so we check for date and segments
      expect(result).toMatch(/27\.03\.2024.*?\d{2}[:.]45/);
    });

    it('returns "Unknown" for null, undefined, 0, or empty string', () => {
      expect(formatDate(null)).toBe('Unknown');
      expect(formatDate(undefined)).toBe('Unknown');
      expect(formatDate(0)).toBe('Unknown');
      expect(formatDate('')).toBe('Unknown');
    });

    it('returns "Invalid Date" for garbage strings', () => {
      expect(formatDate('not-a-date')).toBe('Invalid Date');
    });
  });
});
