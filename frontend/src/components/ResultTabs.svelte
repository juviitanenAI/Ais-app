<script>
  import VesselList from './VesselList.svelte';
  import { vessels } from '../lib/stores.js';

  export let searchTerm = '';

  let activeTab = 'vessels'; // 'vessels' or 'stats'

  function setTab(tab) {
    activeTab = tab;
  }
</script>

<div class="results-container">
  <div class="tabs-header">
    <button 
      class="tab-btn" 
      class:active={activeTab === 'vessels'} 
      onclick={() => setTab('vessels')}
    >
      Vessels ({Object.keys($vessels).length})
    </button>
    <button 
      class="tab-btn" 
      class:active={activeTab === 'stats'} 
      onclick={() => setTab('stats')}
    >
      Stats
    </button>
  </div>

  <div class="tab-content">
    {#if activeTab === 'vessels'}
      <VesselList {searchTerm} />
    {:else if activeTab === 'stats'}
      <div class="stats-placeholder">
        <h3>Vessel Statistics</h3>
        <p>This is where we can show distribution by type, speed averages, etc.</p>
        <div class="coming-soon">Coming Soon...</div>
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

  .coming-soon {
    margin-top: 16px;
    font-style: italic;
    font-size: 12px;
  }
</style>
