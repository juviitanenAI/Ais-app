import { describe, it, expect, beforeEach } from 'vitest';
import { render, cleanup, fireEvent } from '@testing-library/svelte';
import Legend from '../components/Legend.svelte';
import { vessels, vesselTypeCache, legendCollapsed } from '../lib/stores.js';
import * as api from '../lib/api.js';
import { vi } from 'vitest';

describe('Legend Component', () => {
  beforeEach(() => {
    cleanup();
    vessels.set({});
    vesselTypeCache.set({});
    legendCollapsed.set(false);
  });

  it('renders "VESSEL TYPES" title', () => {
    render(Legend);
    expect(document.body.textContent).toContain('VESSEL TYPES');
  });

  it('toggles collapse state when clicking title', async () => {
    render(Legend);
    const title = document.getElementById('legend-toggle');
    
    const legend = document.getElementById('map-legend');
    expect(legend.classList.contains('collapsed')).toBe(false);
    
    await fireEvent.click(title);
    expect(legend.classList.contains('collapsed')).toBe(true);
  });

  it('renders categories from API', async () => {
    const mockCategories = [
      { name: 'cargo', color: '#4a9eff' },
      { name: 'passenger', color: '#2ed573' },
      { name: 'other', color: '#8899aa' }
    ];
    
    vi.spyOn(api, 'fetchVesselCategories').mockResolvedValue(mockCategories);
    
    render(Legend);
    
    // Wait for the async onMount fetch to complete and component to re-render
    await new Promise(resolve => setTimeout(resolve, 10));
    
    const rows = document.querySelectorAll('.legend-row');
    const texts = Array.from(rows).map(r => r.textContent.trim());
    
    expect(texts).toContain('Cargo');
    expect(texts).toContain('Passenger');
    expect(texts).toContain('Other');
  });
});
