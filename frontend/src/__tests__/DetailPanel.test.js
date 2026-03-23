import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/svelte';
import DetailPanel from '../components/DetailPanel.svelte';
import { vessels, activeMmsi, currentSearchResults, selectedMmsis, vesselTypeCache, autoFollow } from '../lib/stores.js';
import { get } from 'svelte/store';

describe('DetailPanel Component', () => {
  beforeEach(() => {
    cleanup();
    activeMmsi.set(null);
    selectedMmsis.set(new Set());
    vesselTypeCache.set({ '70': { category: 'cargo', color: '#444', desc_en: 'Cargo' } });
    vessels.set({});
    currentSearchResults.set([]);
  });

  it('renders nothing clearly when no active MMSI is set', () => {
    render(DetailPanel);
    const panel = document.querySelector('.detail-panel');
    expect(panel.classList.contains('visible')).toBe(false);
  });

  it('shows generic (Unknown) for an unknown MMSI with no data', () => {
    activeMmsi.set('123456789');
    render(DetailPanel);
    
    // Panel should be visible now
    const panel = document.querySelector('.detail-panel');
    expect(panel.classList.contains('visible')).toBe(true);
    
    // Should show Unknown Name
    const nameEl = document.querySelector('.detail-name');
    expect(nameEl.textContent).toBe('(Unknown)');
  });

  it('correctly maps vessel store data to the UI', () => {
    vessels.set({
      '987654321': {
        data: {
          mmsi: '987654321',
          name: 'Test Ship Alpha',
          type: 70, // Cargo
          sog: 14.5,
          cog: 180,
          heading: 182,
          destination: 'Helsinki'
        }
      }
    });

    activeMmsi.set('987654321');
    render(DetailPanel);
    
    expect(document.querySelector('.detail-name').textContent).toBe('Test Ship Alpha');

    // Check grid fields
    const values = Array.from(document.querySelectorAll('.detail-value')).map(el => el.textContent);
    
    expect(values).toContain('987654321'); // mmsi
    expect(values).toContain('Cargo'); // mapped type
    expect(values).toContain('14.5 kn'); // formatted speed
    expect(values).toContain('180°'); // formatted cog
    expect(values).toContain('182°'); // formatted heading
    expect(values).toContain('Helsinki'); // destination
  });

  it('toggles auto-follow when the button is clicked', async () => {
    activeMmsi.set('12345');
    autoFollow.set(false);
    render(DetailPanel);
    
    const followBtn = screen.getByRole('button', { name: /Follow/i });
    expect(followBtn.textContent).toContain('Follow');
    expect(get(autoFollow)).toBe(false);

    await fireEvent.click(followBtn);
    expect(followBtn.textContent).toContain('Following');
    expect(get(autoFollow)).toBe(true);

    await fireEvent.click(followBtn);
    expect(followBtn.textContent).toContain('Follow');
    expect(get(autoFollow)).toBe(false);
  });
});
