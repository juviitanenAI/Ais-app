<script>
  import { sidebarCollapsed, sidebarExpandedAt, vessels, wsConnected, heatmapMode, toggleHeatmapMode, historyMinutes, filterCategories, selectedMmsis, activeMmsi, hideOthers, filteredVessels, activeTab, heatmapLoading } from '../lib/stores.js';
  import { fade } from 'svelte/transition';
  import { APP_VERSION, MOBILE_VERSION } from '../lib/config.js';
  import { fetchVesselCategories, fetchSearchResults } from '../lib/api.js';
  import { onMount } from 'svelte';
  import MultiSelect from './MultiSelect.svelte';
  import ResultTabs from './ResultTabs.svelte';
  import DetailPanel from './DetailPanel.svelte';
  import HistoryToggle from './HistoryToggle.svelte';
  import StatsOverlay from './StatsOverlay.svelte';

  let searchTerm = '';
  let categories = [];

  onMount(async () => {
    try {
      categories = await fetchVesselCategories();
    } catch (e) {
      console.error('Failed to fetch categories:', e);
    }
  });

  $: {
    // Re-fetch search results when filters change
    fetchSearchResults(searchTerm, $filterCategories);
  }

  function clearSelection() {
    selectedMmsis.set(new Set());
    activeMmsi.set(null);
  }

  function toggleSidebar(e) {
    if (e) e.stopPropagation();
    sidebarCollapsed.update(v => {
      if (v) {
        // Expanding: record timestamp to guard against ghost clicks
        sidebarExpandedAt.set(Date.now());
      }
      return !v;
    });
  }
</script>

<div id="sidebar" class:collapsed={$sidebarCollapsed}>
  <div class="sidebar-header">
    <div class="sidebar-title">
      <span class="icon">⚓</span> AIS Tracker
      <span class="version">v{APP_VERSION} - Svelte</span>
    </div>
  </div>

  <div class="stats-bar">
    {#if $heatmapLoading}
      <div class="heatmap-loading-overlay" transition:fade={{duration: 200}}>
        <div class="loading-spinner small"></div>
        <span>Generating heatmap...</span>
      </div>
    {/if}
    <div class="stat left-stat">
      <div class="stat-dot"></div>
      <span id="vessel-count">{$filteredVessels.length}</span> vessels
    </div>
    <div class="mobile-branding">
      ⚓&nbsp;&nbsp; AIS Tracker&nbsp;&nbsp;v<span class="app-version">{MOBILE_VERSION}</span>
    </div>
    <div class="stat right-stat">
      <div class="conn-status" class:connected={$wsConnected}>
        <span class="status-dot"></span>
        {$wsConnected ? 'Live' : 'Offline'}
      </div>
    </div>
  </div>

  {#if $activeTab === 'vessels' || $activeTab === 'heatmap'}
    <div class="search-filter-area" transition:fade={{duration: 150}}>
      {#if $activeTab === 'vessels'}
        <div class="search-box">
          <input type="text" id="search" placeholder="Search vessel name or MMSI…" autocomplete="off" bind:value={searchTerm}/>
        </div>
      {/if}
      <div class="filter-box">
        <MultiSelect {categories} />
      </div>
      {#if $activeTab === 'heatmap' || ($activeTab === 'vessels' && ($selectedMmsis.size > 0 || $activeMmsi))}
        <HistoryToggle />
      {/if}
    </div>
  {/if}

  {#if $selectedMmsis.size > 0 || $activeMmsi}
    <div class="vessel-list-header">
      <div class="header-left">
        <label class="toggle-container">
          <input type="checkbox" id="hide-others" bind:checked={$hideOthers}>
          <span class="toggle-slider"></span>
        </label>
        <span class="hide-others-text">Hide others</span>
      </div>
      <div class="header-actions">
        <button id="deselect-all" class="deselect-all-btn" onclick={clearSelection}>Clear selection</button>
      </div>
    </div>
  {/if}

  <ResultTabs {searchTerm} />
  <DetailPanel />
  <StatsOverlay />

  <button class="sidebar-handle" onclick={toggleSidebar} aria-label="Toggle sidebar"></button>
</div>

<style>
  .heatmap-loading-overlay {
    position: absolute;
    top: 48px; /* Below header */
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(15, 25, 35, 0.7);
    backdrop-filter: blur(2px);
    z-index: 2000;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: var(--accent);
    font-size: 14px;
    font-weight: 600;
    gap: 12px;
  }

  .loading-spinner {
    width: 40px;
    height: 40px;
    border: 3px solid rgba(255, 255, 255, 0.1);
    border-radius: 50%;
    border-top-color: var(--accent-color, #4a9eff);
    animation: spin 1s ease-in-out infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .loading-spinner.small {
    width: 24px;
    height: 24px;
    border-width: 2px;
  }
</style>
