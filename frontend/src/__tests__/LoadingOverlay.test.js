import { describe, it, expect, beforeEach } from 'vitest';
import { render, cleanup } from '@testing-library/svelte';
import LoadingOverlay from '../components/LoadingOverlay.svelte';
import { isLoading, isBackendReady } from '../lib/stores.js';

describe('LoadingOverlay Component', () => {
  beforeEach(() => {
    cleanup();
    isLoading.set(true);
    isBackendReady.set(false);
  });

  it('is visible when isLoading is true', () => {
    render(LoadingOverlay);
    const overlay = document.getElementById('loading-overlay');
    expect(overlay.classList.contains('hidden')).toBe(false);
  });

  it('is hidden when isLoading is false', () => {
    isLoading.set(false);
    render(LoadingOverlay);
    const overlay = document.getElementById('loading-overlay');
    expect(overlay.classList.contains('hidden')).toBe(true);
  });

  it('shows connection message when backend is not ready', () => {
    isBackendReady.set(false);
    render(LoadingOverlay);
    expect(document.body.textContent).toContain('Connecting to maritime backend…');
  });

  it('shows loading message when backend is ready but data is still loading', () => {
    isBackendReady.set(true);
    render(LoadingOverlay);
    expect(document.body.textContent).toContain('Loading vessel data…');
  });
});
