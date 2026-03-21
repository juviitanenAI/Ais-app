<script>
  import { onMount } from 'svelte';
  import { heatmapMode, historyMinutes, filterCategory, vesselTypeCache, vessels, hideOthers, activeMmsi, selectedMmsis } from '../lib/stores.js';
  import { fetchHeatmapData, fetchHistoryData } from '../lib/api.js';
  import { initMap, renderHeatmap, updateMarkerVisibility, renderHistory, clearHistory, fitToVessels } from '../lib/map.js';
  import Legend from './Legend.svelte';

  let mapElement;

  onMount(() => {
    initMap(mapElement);
  });

  // Re-fetch heatmap data whenever toggles change
  $: {
    if ($heatmapMode) {
      fetchHeatmapData($historyMinutes, $filterCategory).then(pts => {
        let color = null;
        if ($filterCategory) {
          const match = Object.values($vesselTypeCache).find(t => t.category === $filterCategory);
          if (match) color = match.color;
        }
        renderHeatmap(pts, color);
      }).catch(e => {
        console.error('Heatmap fetch error', e);
        renderHeatmap([]);
      });
    } else {
      renderHeatmap([]);
    }
  }

  // Reactively hide markers on map when filters or heatmap state changes
  $: {
    const hMode = $heatmapMode;
    const fCat = $filterCategory;
    const hOther = $hideOthers;
    const currentVessels = Object.values($vessels);
    for (const v of currentVessels) {
      if (v.marker) updateMarkerVisibility(v.marker, v.data);
    }
  }

  // Reactively fetch and render history trails for selections
  $: {
    const active = $activeMmsi;
    const selected = Array.from($selectedMmsis);
    const minutes = $historyMinutes;
    const allToTrack = Array.from(new Set([active, ...selected])).filter(Boolean);

    // Skip history if in heatmap mode
    if ($heatmapMode) {
      clearHistory();
    } else {
      clearHistory(); 
      if (allToTrack.length > 0) {
        // First, fit to live positions immediately for responsiveness
        fitToVessels(allToTrack);

        const promises = allToTrack.map(mmsi => 
          fetchHistoryData(mmsi, minutes).then(pts => {
            renderHistory(mmsi, pts);
          }).catch(e => console.error(`History fetch error for ${mmsi}`, e))
        );

        // Then, re-fit once history is loaded to include the trails
        Promise.all(promises).then(() => {
          fitToVessels(allToTrack);
        });
      }
    }
  }
</script>

<div id="map-container">
  <div id="map" bind:this={mapElement}></div>
  <Legend />
</div>

<style>
  #map-container {
    flex: 1;
    position: relative;
    height: 100vh;
  }
  #map {
    width: 100%;
    height: 100%;
  }
</style>
