import { render, fireEvent } from '@testing-library/svelte';
import { get } from 'svelte/store';
import Sidebar from '../components/Sidebar.svelte';
import { sidebarCollapsed } from '../lib/stores.js';
import { describe, it, expect, beforeEach } from 'vitest';

describe('Sidebar Component Minimization (Mobile)', () => {
  beforeEach(() => {
    sidebarCollapsed.set(false);
  });

  it('renders the mobile drawer handle', () => {
    render(Sidebar);
    const handle = document.querySelector('.sidebar-handle');
    expect(handle).toBeTruthy();
    expect(handle.getAttribute('aria-label')).toBe('Toggle sidebar');
  });

  it('toggles sidebarCollapsed store when handle is clicked', async () => {
    render(Sidebar);
    const handle = document.querySelector('.sidebar-handle');
    
    // Initial state
    expect(get(sidebarCollapsed)).toBe(false);
    
    // Click to collapse
    await fireEvent.pointerDown(handle);
    expect(get(sidebarCollapsed)).toBe(true);
    
    // Click to expand
    await fireEvent.pointerDown(handle);
    expect(get(sidebarCollapsed)).toBe(false);
  });
});
