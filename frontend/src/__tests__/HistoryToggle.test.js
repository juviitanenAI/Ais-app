import { describe, it, expect, beforeEach } from 'vitest';
import { render, cleanup, fireEvent } from '@testing-library/svelte';
import HistoryToggle from '../components/HistoryToggle.svelte';
import { heatmapMode, historyMinutes } from '../lib/stores.js';
import { get } from 'svelte/store';

describe('HistoryToggle Component', () => {
  beforeEach(() => {
    cleanup();
    heatmapMode.set(false);
    historyMinutes.set(180);
  });

  it('renders normal options when heatmapMode is false', () => {
    render(HistoryToggle);
    const buttons = document.querySelectorAll('.history-btn');
    const labels = Array.from(buttons).map(b => b.textContent.trim());
    
    expect(labels).toEqual(['1h', '3h', '12h', '24h']);
  });

  it('renders heatmap options when heatmapMode is true', async () => {
    heatmapMode.set(true);
    render(HistoryToggle);
    
    const buttons = document.querySelectorAll('.history-btn');
    const labels = Array.from(buttons).map(b => b.textContent.trim());
    
    expect(labels).toEqual(['12h', '24h', '3 days', '1 wk']);
  });

  it('updates historyMinutes store when a button is clicked', async () => {
    render(HistoryToggle);
    const buttons = document.querySelectorAll('.history-btn');
    
    // Click '1h' (60 minutes)
    await fireEvent.click(buttons[0]);
    expect(get(historyMinutes)).toBe(60);
    
    // Click '24h' (1440 minutes)
    await fireEvent.click(buttons[3]);
    expect(get(historyMinutes)).toBe(1440);
  });

  it('sets active class on the currently selected option', () => {
    historyMinutes.set(720); // 12h
    render(HistoryToggle);
    
    const buttons = document.querySelectorAll('.history-btn');
    expect(buttons[2].classList.contains('active')).toBe(true);
    expect(buttons[0].classList.contains('active')).toBe(false);
  });
});
