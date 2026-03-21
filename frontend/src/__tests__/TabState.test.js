import { get } from 'svelte/store';
import { heatmapMode, activeTab, toggleHeatmapMode, switchSecondaryTab } from '../lib/stores.js';
import { describe, it, expect, beforeEach } from 'vitest';

describe('Tab and Heatmap State Management', () => {
  beforeEach(() => {
    // Reset state before each test
    heatmapMode.set(false);
    activeTab.set('vessels');
  });

  it('activating heatmap mode automatically switches to stats tab', () => {
    toggleHeatmapMode(true);
    expect(get(heatmapMode)).toBe(true);
    expect(get(activeTab)).toBe('stats');
  });

  it('deactivating heatmap mode switches back to vessels tab', () => {
    toggleHeatmapMode(true); // first enable it
    toggleHeatmapMode(false);
    expect(get(heatmapMode)).toBe(false);
    expect(get(activeTab)).toBe('vessels');
  });

  it('switching to vessels tab automatically disables heatmap mode', () => {
    toggleHeatmapMode(true); // first enable heatmap
    
    switchSecondaryTab('vessels');
    expect(get(activeTab)).toBe('vessels');
    expect(get(heatmapMode)).toBe(false);
  });

  it('switching to stats tab does not automatically enable heatmap mode', () => {
    switchSecondaryTab('stats');
    expect(get(activeTab)).toBe('stats');
    expect(get(heatmapMode)).toBe(false);
  });
});
