import { describe, it, expect, beforeEach } from 'vitest';
import { render, cleanup, fireEvent } from '@testing-library/svelte';
import ResultTabs from '../components/ResultTabs.svelte';
import { vessels } from '../lib/stores.js';

describe('ResultTabs Component', () => {
  beforeEach(() => {
    cleanup();
    vessels.set({});
  });

  it('renders both tab buttons', () => {
    const { getByText } = render(ResultTabs);
    expect(getByText(/Vessels/)).toBeDefined();
    expect(getByText('Stats')).toBeDefined();
  });

  it('shows vessel count in the tab button', () => {
    vessels.set({
      '1': { data: { name: 'V1' } },
      '2': { data: { name: 'V2' } }
    });
    const { getByText } = render(ResultTabs);
    expect(getByText('Vessels (2)')).toBeDefined();
  });

  it('switches between tabs when clicked', async () => {
    const { getByText, queryByText } = render(ResultTabs);
    
    // Initially on vessels tab
    expect(document.querySelector('.vessel-list')).toBeDefined();
    expect(queryByText('Vessel Statistics')).toBeNull();

    // Click Stats tab
    const statsBtn = getByText('Stats');
    await fireEvent.click(statsBtn);

    // Now on stats tab
    expect(queryByText('Vessel Statistics')).toBeDefined();
    expect(document.querySelector('.vessel-list')).toBeNull();

    // Click Vessels tab back
    const vesselsBtn = getByText(/Vessels/);
    await fireEvent.click(vesselsBtn);

    // Back to vessels tab
    expect(document.querySelector('.vessel-list')).toBeDefined();
  });

  it('passes searchTerm down to VesselList', () => {
    vessels.set({
      '123456789': { 
        data: { mmsi: '123456789', name: 'TITANIC' },
        lastUpdate: Date.now()
      }
    });
    
    // Search for something else
    const { queryByText } = render(ResultTabs, { searchTerm: 'OAK' });
    expect(queryByText('TITANIC')).toBeNull();
    expect(queryByText('No vessels found')).toBeDefined();

    cleanup();

    // Search for match
    const { getByText } = render(ResultTabs, { searchTerm: 'TITANIC' });
    expect(getByText('TITANIC')).toBeDefined();
  });
});
