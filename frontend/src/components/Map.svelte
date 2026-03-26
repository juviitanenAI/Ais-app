<script>
  import { onMount } from 'svelte';
  import { heatmapMode, heatmapLoading, historyMinutes, filterCategories, vesselTypeCache, vessels, buoys, hideOthers, activeMmsi, selectedMmsis, activeBuoySite } from '../lib/stores.js';
  import { fetchHeatmapData, fetchHistoryData } from '../lib/api.js';
  import { initMap, map, renderHeatmap, updateMarkerVisibility, updateBuoyVisibility, renderHistory, clearHistory, fitToVessels, buoyMarkers } from '../lib/map.js';
  import Legend from './Legend.svelte';

  let mapElement;

  onMount(() => {
    initMap(mapElement);
  });

  // Re-fetch heatmap data whenever toggles change
  $: {
    if ($heatmapMode && map) {
      const hCat = $filterCategories.length === 1 ? $filterCategories[0] : 'all';
      heatmapLoading.set(true);
      fetchHeatmapData($historyMinutes, hCat).then(pts => {
        let color = null;
        if (hCat !== 'all') {
          const match = Object.values($vesselTypeCache).find(t => t.category === hCat);
          if (match) color = match.color;
        }
        renderHeatmap(pts, color);
      }).catch(e => {
        console.error('Heatmap fetch error', e);
        renderHeatmap([]);
      }).finally(() => {
        heatmapLoading.set(false);
      });
    } else {
      clearHistory();
    }
  }

  // Reactively hide markers on map when filters or heatmap state changes
  $: {
    const fCats = $filterCategories;
    const hMode = $heatmapMode;
    if (Object.keys($vessels).length > 0) {
      Object.values($vessels).forEach(v => updateMarkerVisibility(v.marker, v.data));
    }
    if (buoyMarkers.size > 0) {
      buoyMarkers.forEach(marker => updateBuoyVisibility(marker));
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

  // Reactively update marker highlights and selection ring
  import { updateHighlights } from '../lib/map.js';
  $: {
    updateHighlights($activeMmsi, $selectedMmsis, $activeBuoySite);
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
