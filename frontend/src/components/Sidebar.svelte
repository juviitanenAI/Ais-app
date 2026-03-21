<script>
  import { sidebarCollapsed, vessels, wsConnected, heatmapMode, historyMinutes, filterCategory, selectedMmsis, activeMmsi, hideOthers } from '../lib/stores.js';
  import { APP_VERSION, MOBILE_VERSION } from '../lib/config.js';
  import ResultTabs from './ResultTabs.svelte';
  import DetailPanel from './DetailPanel.svelte';
  import HistoryToggle from './HistoryToggle.svelte';

  let searchTerm = '';

  function clearSelection() {
    selectedMmsis.set(new Set());
    activeMmsi.set(null);
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
      <span id="vessel-count">{Object.keys($vessels).length}</span> vessels
    </div>
    <div class="mobile-branding">
      ⚓&nbsp;&nbsp; AIS Tracker&nbsp;&nbsp;v<span class="app-version">{MOBILE_VERSION}</span>
    </div>
    <div class="stat right-stat">
      {#if $heatmapMode}
        <button id="heatmap-toggle" class="heatmap-btn active" onclick={() => heatmapMode.set(false)}>🔥 Heatmap</button>
      {:else}
        <button id="live-toggle" class="heatmap-btn" onclick={() => heatmapMode.set(true)}>Live ●</button>
      {/if}
      <button id="mobile-list-close" class="mobile-list-close" title="Close List" onclick={() => $sidebarCollapsed = true}>✕</button>
    </div>
  </div>

  <div class="search-filter-area">
    <div class="search-box">
      <input type="text" id="search" placeholder="Search vessel name or MMSI…" autocomplete="off" bind:value={searchTerm}/>
    </div>
    <div class="filter-box">
      <select id="type-filter" bind:value={$filterCategory}>
        <option value="">All Vessel Types</option>
        <option value="cargo">Cargo</option>
        <option value="tanker">Tanker</option>
        <option value="passenger">Passenger</option>
        <option value="fishing">Fishing</option>
        <option value="other">Other</option>
      </select>
    </div>
    <HistoryToggle />
  </div>

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
</div>
