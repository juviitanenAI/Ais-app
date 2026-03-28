import { describe, it, expect, beforeEach } from 'vitest';
import { render, cleanup, fireEvent } from '@testing-library/svelte';
import HistoryToggle from '../components/HistoryToggle.svelte';
import { heatmapMode, historyMinutes } from '../lib/stores.js';
import { get } from 'svelte/store';
import { tick } from 'svelte';

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

  it('automatically resets historyMinutes to the first option when current value is invalid for mode', async () => {
    // 1. Start with normal mode at 1h (60m)
    heatmapMode.set(false);
    historyMinutes.set(60);
    render(HistoryToggle);
    
    expect(get(historyMinutes)).toBe(60);
    
    // 2. Switch to heatmap mode
    // Heatmap options start at 12h (720m). 60m is NOT valid.
    heatmapMode.set(true);
    await tick();
    
    // Svelte's reactive statement should trigger
    // Wait for store update
    expect(get(historyMinutes)).toBe(720);
    
    // 3. Switch back to normal mode
    // Normal mode options max out at 24h (1440m).
    // Let's set a value ONLY in heatmap mode (e.g., 3 days = 4320m)
    historyMinutes.set(4320);
    heatmapMode.set(false);
    await tick();
    
    expect(get(historyMinutes)).toBe(60); // First normal option
  });

  it('preserves historyMinutes if it is valid in both modes', async () => {
    // 12h (720m) is valid in both
    heatmapMode.set(false);
    historyMinutes.set(720);
    render(HistoryToggle);
    await tick();
    
    expect(get(historyMinutes)).toBe(720);
    
    heatmapMode.set(true);
    await tick();
    expect(get(historyMinutes)).toBe(720);
  });
});
