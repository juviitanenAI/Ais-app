<script>
  import VesselList from './VesselList.svelte';
  import BuoyList from './BuoyList.svelte';
  import { vessels, filteredVessels, buoys, activeTab, switchSecondaryTab, showStatsOverlay, heatmapLoading } from '../lib/stores.js';

  export let searchTerm = '';
</script>

<div class="results-container">
  <div class="tabs-header">
    <button 
      class="tab-btn" 
      class:active={$activeTab === 'vessels'} 
      onclick={() => switchSecondaryTab('vessels')}
    >
      Vessels ({$filteredVessels.length})
    </button>
    <button 
      class="tab-btn" 
      class:active={$activeTab === 'buoys'} 
      onclick={() => switchSecondaryTab('buoys')}
    >
      Buoys ({$buoys.length})
    </button>
    <button 
      class="tab-btn" 
      class:active={$activeTab === 'heatmap'} 
      onclick={() => switchSecondaryTab('heatmap')}
    >
      Heatmap
    </button>
    <button 
      class="tab-btn" 
      class:active={$activeTab === 'stats'} 
      onclick={() => switchSecondaryTab('stats')}
    >
      Stats
    </button>
  </div>

  <div class="tab-content">
    {#if $activeTab === 'vessels'}
      <VesselList {searchTerm} />
    {:else if $activeTab === 'buoys'}
      <BuoyList {searchTerm} />
    {:else if $activeTab === 'heatmap'}
      <div class="stats-placeholder">
        <h3>Route Heatmap</h3>
          <p>Visualizing vessel traffic density over time. Use history and category filters above to refine the view.</p>
          <div class="heatmap-info">
            The heatmap is generated from historical samples (15-min intervals).
          </div>
      </div>
    {:else if $activeTab === 'stats'}
      <div class="stats-placeholder">
        <h3>Vessel Statistics</h3>
        <p>View historical vessel activity trends and category distributions.</p>
        <button class="open-plots-btn" onclick={() => showStatsOverlay.set(true)}>Open Plots</button>
      </div>
    {/if}
  </div>
</div>

<style>
  .results-container {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0; /* Important for scrolling */
  }

  .tabs-header {
    display: flex;
    border-bottom: 1px solid var(--border-color, #333);
    background: var(--bg-secondary, #1a1a1a);
    padding: 0 8px;
  }

  .tab-btn {
    background: none;
    border: none;
    padding: 10px 16px;
    color: var(--text-muted, #888);
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    border-bottom: 2px solid transparent;
    transition: all 0.2s;
  }

  .tab-btn:hover {
    color: var(--text-color, #fff);
  }

  .tab-btn.active {
    color: var(--accent-color, #4a9eff);
    border-bottom-color: var(--accent-color, #4a9eff);
  }

  .tab-content {
    flex: 1;
    overflow-y: auto;
    position: relative;
  }

  .stats-placeholder {
    padding: 24px;
    text-align: center;
    color: var(--text-muted, #888);
  }

  .stats-placeholder h3 {
    margin-top: 0;
    color: var(--text-color, #fff);
  }

  .heatmap-info {
    margin-top: 16px;
    font-size: 12px;
    font-style: italic;
    color: var(--text-muted, #888);
  }



  .open-plots-btn {
    margin-top: 20px;
    padding: 10px 20px;
    background: var(--accent-color, #4a9eff);
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
    transition: background 0.2s, transform 0.1s;
  }
  .open-plots-btn:hover {
    background: #3a8eef;
  }
  .open-plots-btn:active {
    transform: scale(0.98);
  }
</style>
