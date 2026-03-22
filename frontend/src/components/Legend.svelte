<script>
  import { legendCollapsed } from '../lib/stores.js';
  import { fetchVesselCategories } from '../lib/api.js';
  import { onMount } from 'svelte';
 
  let categories = [];
  onMount(async () => {
    try {
      categories = await fetchVesselCategories();
    } catch (e) {
      console.error('Failed to fetch categories for legend:', e);
    }
  });

  // Dynamically update parent offset variable
  $: if (typeof document !== 'undefined') {
    const root = document.getElementById('map-container');
    if (root) {
      root.style.setProperty('--control-offset', $legendCollapsed ? '80px' : '200px');
    }
  }
</script>

<div class="map-legend" class:collapsed={$legendCollapsed} id="map-legend">
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="legend-title" id="legend-toggle" onclick={() => $legendCollapsed = !$legendCollapsed}>
    VESSEL TYPES <span class="toggle-icon">▾</span>
  </div>
  <div id="map-legend-items">
    {#each categories as cat (cat.name)}
      <div class="legend-row">
        <div class="legend-dot" style="background:{cat.color}"></div> 
        <span class="legend-label">{cat.name.charAt(0).toUpperCase() + cat.name.slice(1)}</span>
      </div>
    {/each}
  </div>
</div>

<style>
  .map-legend {
    position: absolute;
    top: 10px;
    right: 10px;
    z-index: 1000;
    font-size: 10px; /* Reduced for compactness */
    padding: 8px 12px;
    background: rgba(26, 34, 46, 0.95); /* Slightly more opaque */
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px; /* Softer corners */
    color: white;
    backdrop-filter: blur(8px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    width: 130px; /* Fixed width for stability */
  }
  .map-legend.collapsed #map-legend-items {
    display: none;
  }
  .legend-title {
    font-size: 11px;
    font-weight: 600;
    margin-bottom: 4px;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
  }
  .legend-row {
    display: flex;
    align-items: center;
    margin: 2px 0;
    gap: 6px;
  }
  .legend-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }
  .toggle-icon {
    font-size: 9px;
    opacity: 0.6;
  }
  
  :global(.leaflet-control-layers) {
    margin-top: var(--control-offset, 200px) !important;
    transition: margin-top 0.3s ease;
    z-index: 1100 !important;
  }

  :global(.leaflet-top.leaflet-right) {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
  }
</style>
