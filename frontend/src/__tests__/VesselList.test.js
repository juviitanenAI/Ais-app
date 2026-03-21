import { describe, it, expect, beforeEach } from 'vitest';
import { render, cleanup } from '@testing-library/svelte';
import VesselList from '../components/VesselList.svelte';
import { vessels, selectedMmsis, activeMmsi } from '../lib/stores.js';

describe('VesselList Component', () => {
  beforeEach(() => {
    cleanup();
    vessels.set({});
    selectedMmsis.set(new Set());
    activeMmsi.set(null);
  });

  it('displays "No vessels found" when empty', () => {
    render(VesselList);
    const text = document.querySelector('.vessel-list').textContent;
    expect(text).toContain('No vessels found');
  });

  it('renders a list of vessels and formats speed and time properly', () => {
    vessels.set({
      '111111111': {
        lastUpdate: new Date('2026-03-21T12:00:00Z').getTime(),
        data: {
          mmsi: '111111111',
          name: 'Speedy',
          sog: 20.5,
          type: 60 // Passenger
        }
      }
    });

    render(VesselList);
    
    const text = document.querySelector('.vessel-list').textContent;
    expect(text).not.toContain('No vessels found');
    expect(text).toContain('Speedy');
    expect(text).toContain('111111111');
    expect(text).toContain('20.5 kn'); // Formatted Speed
  });
});
