import { describe, it, expect, beforeEach } from 'vitest';
import { render, cleanup } from '@testing-library/svelte';
import LoadingOverlay from '../components/LoadingOverlay.svelte';
import { isLoading } from '../lib/stores.js';

describe('LoadingOverlay Component', () => {
  beforeEach(() => {
    cleanup();
    isLoading.set(true);
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

  it('shows the correct loading text', () => {
    render(LoadingOverlay);
    expect(document.body.textContent).toContain('Loading vessel data…');
  });
});
