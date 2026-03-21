import { describe, it, expect, beforeEach, vi } from 'vitest';
import { fetchSearchResults, fetchLiveVesselData, fetchHistoryData, fetchVesselTypes, fetchHeatmapData } from '../lib/api.js';
import { currentSearchResults, vesselTypeCache } from '../lib/stores.js';
import { get } from 'svelte/store';

// Mock fetch
global.fetch = vi.fn();

describe('API Functions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    currentSearchResults.set([]);
    vesselTypeCache.set({});
  });

  describe('fetchSearchResults', () => {
    it('calls fetch with correct URL and updates store', async () => {
      const mockResult = [{ mmsi: 123, name: 'Test' }];
      fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResult)
      });

      await fetchSearchResults('query', ['cargo']);
      
      expect(fetch).toHaveBeenCalledWith(expect.stringContaining('q=query'));
      expect(fetch).toHaveBeenCalledWith(expect.stringContaining('category=cargo'));
      expect(get(currentSearchResults)).toEqual(mockResult);
    });
  });

  describe('fetchLiveVesselData', () => {
    it('returns json data if ok', async () => {
      const mockResult = { '123': { data: {} } };
      fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResult)
      });

      const result = await fetchLiveVesselData();
      expect(result).toEqual(mockResult);
    });

    it('throws error if not ok', async () => {
      fetch.mockResolvedValue({ ok: false, status: 500 });
      await expect(fetchLiveVesselData()).rejects.toThrow('HTTP 500');
    });
  });

  describe('fetchHistoryData', () => {
    it('returns array for specific mmsi', async () => {
      const mmsi = '123';
      const mockResult = { [mmsi]: [{ lat: 1, lon: 2 }] };
      fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResult)
      });

      const result = await fetchHistoryData(mmsi, 60);
      expect(result).toEqual(mockResult[mmsi]);
    });
  });

  describe('fetchVesselTypes', () => {
    it('updates vesselTypeCache', async () => {
      const mockResult = { '70': { category: 'cargo' } };
      fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResult)
      });

      await fetchVesselTypes();
      expect(get(vesselTypeCache)).toEqual(mockResult);
    });
  });

  describe('fetchHeatmapData', () => {
    it('calls fetch with correct params', async () => {
      const mockResult = [{ lat: 1, lon: 2, weight: 0.5 }];
      fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResult)
      });

      const result = await fetchHeatmapData(180, 'cargo');
      expect(fetch).toHaveBeenCalledWith(expect.stringContaining('minutes=180'));
      expect(fetch).toHaveBeenCalledWith(expect.stringContaining('category=cargo'));
      expect(result).toEqual(mockResult);
    });
  });
});
