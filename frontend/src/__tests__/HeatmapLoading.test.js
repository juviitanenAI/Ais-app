import { render, cleanup } from '@testing-library/svelte';
import { heatmapLoading } from '../lib/stores.js';
import Sidebar from '../components/Sidebar.svelte';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import * as api from '../lib/api.js';

describe('Heatmap Loading Overlay in Sidebar', () => {
  beforeEach(() => {
    cleanup();
    heatmapLoading.set(false);
    // Mock API calls that Sidebar triggers on mount
    vi.spyOn(api, 'fetchVesselCategories').mockResolvedValue([]);
    vi.spyOn(api, 'fetchSearchResults').mockResolvedValue(undefined);
  });

  it('does not show loading overlay by default', () => {
    render(Sidebar);
    const overlay = document.querySelector('.heatmap-loading-overlay');
    expect(overlay).toBeNull();
  });

  it('shows loading overlay when heatmapLoading is true', async () => {
    heatmapLoading.set(true);
    render(Sidebar);
    
    const overlay = document.querySelector('.heatmap-loading-overlay');
    expect(overlay).toBeTruthy();
    
    const text = overlay.textContent;
    expect(text).toContain('Generating heatmap...');
    
    const spinner = overlay.querySelector('.loading-spinner');
    expect(spinner).toBeTruthy();
  });
});
