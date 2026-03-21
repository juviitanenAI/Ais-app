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
    font-size: 11px;
    padding: 6px 10px;
    background: rgba(26, 34, 46, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 4px;
    color: white;
    backdrop-filter: blur(4px);
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
  
  /* Push Leaflet's layer selector down to accommodate the legend above it */
  :global(.leaflet-control-layers) {
    margin-top: 160px !important;
  }
  .map-legend.collapsed + :global(.leaflet-control-layers) {
    margin-top: 50px !important;
  }
  /* Since they aren't siblings in the DOM, we can't use + selector easily, 
     so we'll just use a safe fixed margin or handle it via a shared state. 
     For now, 150px is a safe offset for the most common 6-row legend. */
  :global(.leaflet-top.leaflet-right) {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
  }
</style>
