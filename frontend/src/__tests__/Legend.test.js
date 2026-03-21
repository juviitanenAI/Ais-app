import { describe, it, expect, beforeEach } from 'vitest';
import { render, cleanup, fireEvent } from '@testing-library/svelte';
import Legend from '../components/Legend.svelte';
import { vessels, vesselTypeCache, legendCollapsed } from '../lib/stores.js';

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

  it('renders categories from vessels and cache', () => {
    vesselTypeCache.set({
      '70': { category: 'cargo', color: '#4a9eff' },
      '60': { category: 'passenger', color: '#2ed573' }
    });
    
    vessels.set({
      '1': { data: { vtype_info: { category: 'cargo' } } },
      '2': { data: { vtype_info: { category: 'passenger' } } }
    });

    render(Legend);
    
    const rows = document.querySelectorAll('.legend-row');
    const texts = Array.from(rows).map(r => r.textContent.trim());
    
    expect(texts).toContain('Cargo');
    expect(texts).toContain('Passenger');
    expect(texts).toContain('Other');
  });
});
