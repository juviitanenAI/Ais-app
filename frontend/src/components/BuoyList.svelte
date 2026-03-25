<script>
  import { buoys, activeBuoySite } from '../lib/stores.js';
  import { getContext } from 'svelte';

  export let searchTerm = '';

  const { focusOnBuoy } = getContext('mapActions');

  $: filteredBuoys = $buoys.filter(b => {
    if (!searchTerm) return true;
    const name = (b.data.siteName || '').toLowerCase();
    const siteNum = String(b.data.siteNumber);
    const term = searchTerm.toLowerCase();
    return name.includes(term) || siteNum.includes(term);
  }).sort((a, b) => (a.data.siteName || '').localeCompare(b.data.siteName || ''));

  function selectBuoy(buoy) {
    activeBuoySite.set(buoy.data.siteNumber);
    focusOnBuoy(buoy);
  }

  function getTrendIcon(trend) {
    switch (trend) {
      case 'RISING': return '↗️';
      case 'FALLING': return '↘️';
      case 'CONSTANT': return '➡️';
      default: return '';
    }
  }

  function getSeaStateColor(state) {
    if (!state) return 'inherit';
    switch (state.toUpperCase()) {
      case 'CALM': return '#4a9eff';
      case 'MODERATE': return '#ffcc00';
      case 'ROUGH': return '#ff3300';
      default: return 'inherit';
    }
  }
</script>

<div class="buoy-list">
  {#if filteredBuoys.length === 0}
    <div class="empty-state">No buoys found</div>
  {:else}
    {#each filteredBuoys as buoy (buoy.data.siteNumber)}
      <div 
        class="buoy-item" 
        class:active={$activeBuoySite === buoy.data.siteNumber}
        onclick={() => selectBuoy(buoy)}
        onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && selectBuoy(buoy)}
        role="button"
        tabindex="0"
      >
        <div class="buoy-header">
          <span class="buoy-name">{buoy.data.siteName || 'Unknown Site'}</span>
          <span class="buoy-number">#{buoy.data.siteNumber}</span>
        </div>
        
        <div class="buoy-details">
          <div class="detail-row">
            <span class="label">Type:</span>
            <span class="value">{buoy.data.siteType}</span>
          </div>
          
          {#if buoy.data.temperature !== null}
            <div class="detail-row">
              <span class="label">Temp:</span>
              <span class="value">{buoy.data.temperature}°C</span>
            </div>
          {/if}

          {#if buoy.data.seaState}
            <div class="detail-row">
              <span class="label">Sea:</span>
              <span class="value" style="color: {getSeaStateColor(buoy.data.seaState)}">
                {buoy.data.seaState} {getTrendIcon(buoy.data.trend)}
              </span>
            </div>
          {/if}
        </div>
        
        <div class="buoy-footer">
          <span class="update-time">Updated: {new Date(buoy.data.lastUpdate).toLocaleTimeString()}</span>
        </div>
      </div>
    {/each}
  {/if}
</div>

<style>
  .buoy-list {
    display: flex;
    flex-direction: column;
  }

  .empty-state {
    padding: 32px;
    text-align: center;
    color: var(--text-muted, #888);
  }

  .buoy-item {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border-color, #333);
    cursor: pointer;
    transition: background 0.2s;
  }

  .buoy-item:hover {
    background: var(--bg-hover, #2a2a2a);
  }

  .buoy-item.active {
    background: var(--bg-active, #333);
    border-left: 3px solid var(--accent-color, #4a9eff);
  }

  .buoy-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
  }

  .buoy-name {
    font-weight: 600;
    font-size: 14px;
    color: var(--text-color, #fff);
  }

  .buoy-number {
    font-size: 11px;
    color: var(--text-muted, #888);
  }

  .buoy-details {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px 12px;
    margin-bottom: 4px;
  }

  .detail-row {
    font-size: 12px;
  }

  .label {
    color: var(--text-muted, #888);
    margin-right: 4px;
  }

  .value {
    color: var(--text-color, #eee);
  }

  .buoy-footer {
    font-size: 10px;
    color: var(--text-muted, #666);
    text-align: right;
  }
</style>
