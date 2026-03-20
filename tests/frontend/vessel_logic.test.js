import { describe, it, expect } from 'vitest';
import { compareVessels, filterVessels } from '../../app/static/js/utils.js';

describe('Vessel Logic Helpers', () => {
  describe('compareVessels', () => {
    const activeMmsi = '111';
    const selectedMmsis = new Set(['222']);

    it('should put pinned vessels at the top', () => {
      const a = { mmsi: '222', name: 'B Ship' }; // Pinned
      const b = { mmsi: '333', name: 'A Ship' }; // Not pinned
      expect(compareVessels(a, b, selectedMmsis, null)).toBe(-1);
    });

    it('should put active vessel at the top', () => {
      const a = { mmsi: '111', name: 'Z Ship' }; // Active
      const b = { mmsi: '444', name: 'A Ship' }; // Normal
      expect(compareVessels(a, b, new Set(), activeMmsi)).toBe(-1);
    });

    it('should sort alphabetically if neither is selected', () => {
      const a = { mmsi: '333', name: 'B Ship' };
      const b = { mmsi: '444', name: 'A Ship' };
      expect(compareVessels(a, b, new Set(), null)).toBeGreaterThan(0);
      expect(compareVessels(b, a, new Set(), null)).toBeLessThan(0);
    });

    it('should handle missing names by treating them as zzz', () => {
      const a = { mmsi: '333', name: null };
      const b = { mmsi: '444', name: 'A Ship' };
      expect(compareVessels(a, b, new Set(), null)).toBeGreaterThan(0);
    });

    it('should ignore case when sorting by name', () => {
      const a = { mmsi: '333', name: 'b ship' };
      const b = { mmsi: '444', name: 'A Ship' };
      expect(compareVessels(a, b, new Set(), null)).toBeGreaterThan(0);
    });
  });

  describe('filterVessels', () => {
    const vessels = [
      { mmsi: '123456', name: 'Arctic Explorer' },
      { mmsi: '654321', name: 'Baltic Queen' },
      { mmsi: '789000', name: 'Cargo Master' }
    ];

    it('should return all vessels if search is empty', () => {
      expect(filterVessels(vessels, '').length).toBe(3);
    });

    it('should filter by name (case insensitive)', () => {
      const result = filterVessels(vessels, 'arctic');
      expect(result.length).toBe(1);
      expect(result[0].mmsi).toBe('123456');
    });

    it('should filter by MMSI', () => {
      const result = filterVessels(vessels, '654');
      expect(result.length).toBe(1);
      expect(result[0].name).toBe('Baltic Queen');
    });

    it('should return empty array if no match', () => {
      expect(filterVessels(vessels, 'nonexistent').length).toBe(0);
    });
  });
});
