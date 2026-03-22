<script>
  import { sidebarCollapsed, vessels, wsConnected, heatmapMode, toggleHeatmapMode, historyMinutes, filterCategories, selectedMmsis, activeMmsi, hideOthers, filteredVessels, activeTab } from '../lib/stores.js';
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
    sidebarCollapsed.update(v => !v);
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

  <button class="sidebar-handle" onpointerdown={toggleSidebar} aria-label="Toggle sidebar"></button>
</div>
