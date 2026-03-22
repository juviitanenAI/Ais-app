import { render, cleanup } from '@testing-library/svelte';
import Sidebar from '../components/Sidebar.svelte';
import { activeTab, selectedMmsis, activeMmsi } from '../lib/stores.js';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import * as api from '../lib/api.js';

describe('Sidebar Filter Visibility', () => {
  beforeEach(() => {
    cleanup();
    selectedMmsis.set(new Set());
    activeMmsi.set(null);
    vi.spyOn(api, 'fetchVesselCategories').mockResolvedValue([]);
    vi.spyOn(api, 'fetchSearchResults').mockResolvedValue(undefined);
  });

  it('shows search, category, but NOT history in Vessels tab when nothing selected', () => {
    activeTab.set('vessels');
    render(Sidebar);
    
    expect(document.querySelector('.search-box')).toBeTruthy();
    expect(document.querySelector('.filter-box')).toBeTruthy();
    expect(document.querySelector('.history-controls')).toBeNull();
  });

  it('shows history in Vessels tab when a vessel is selected', () => {
    activeTab.set('vessels');
    activeMmsi.set('123456789');
    render(Sidebar);
    
    expect(document.querySelector('.history-controls')).toBeTruthy();
  });

  it('hides search but shows category and history in Heatmap tab regardless of selection', () => {
    activeTab.set('heatmap');
    render(Sidebar);
    
    expect(document.querySelector('.search-box')).toBeNull();
    expect(document.querySelector('.filter-box')).toBeTruthy();
    expect(document.querySelector('.history-controls')).toBeTruthy();
  });

  it('hides search, category, and history in Stats tab', () => {
    activeTab.set('stats');
    render(Sidebar);
    
    expect(document.querySelector('.search-box')).toBeNull();
    expect(document.querySelector('.filter-box')).toBeNull();
    expect(document.querySelector('.history-controls')).toBeNull();
  });
});
