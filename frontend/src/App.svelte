<script>
  import { onMount, setContext } from 'svelte';
  import Sidebar from './components/Sidebar.svelte';
  import Map from './components/Map.svelte';
  import LoadingOverlay from './components/LoadingOverlay.svelte';
  import { sidebarCollapsed, isLoading, activeMmsi } from './lib/stores.js';
  import { fetchVesselTypes, fetchLiveVesselData, fetchSearchResults } from './lib/api.js';
  import { connectWebSocket } from './lib/ws.js';
  import { addOrUpdateVessel, map as leafMap, setAutoFollow } from './lib/map.js';
  import { vessels as vesselsStore } from './lib/stores.js';
  import { vesselTypeInfo, shipIcon } from './lib/utils.js';
  import { get } from 'svelte/store';

  function handleSelectVessel(mmsi) {
    activeMmsi.set(mmsi);
    setAutoFollow(true);
    // Detail panel opening logic will react to activeMmsi
    sidebarCollapsed.set(false);
  }

  onMount(async () => {
    try {
      await fetchVesselTypes();
      const data = await fetchLiveVesselData();
      
      // Batch initial load to avoid 800 store updates
      vesselsStore.update(vs => {
        data.forEach(v => {
          const mmsi = v.mmsi;
          const { color } = vesselTypeInfo(v.type, v.vtype_info);
          const heading = v.heading ?? v.cog ?? 0;
          
          const marker = window.L.marker([v.lat, v.lon], { 
            icon: shipIcon(color, heading, false, false), 
            title: v.name || mmsi 
          });
          marker.on('click', () => handleSelectVessel(mmsi));
          
          if (leafMap) marker.addTo(leafMap);
          vs[mmsi] = { marker, data: v, lastUpdate: Date.now() };
        });
        return { ...vs };
      });
      
      await fetchSearchResults();
      isLoading.set(false);
    } catch (e) {
      console.error('[load] Failed to fetch live vessels:', e);
      setTimeout(() => isLoading.set(false), 2000);
    }

    connectWebSocket(handleSelectVessel);
  });
</script>

<LoadingOverlay />

<!-- Original map_ui.html had #app and .sidebar-visible on the same div. Svelte mounts INSIDE #app. 
     We can just add the class to the document body or wrap it here. -->
<div class="app-container" class:sidebar-visible={!$sidebarCollapsed}>
  <Sidebar />
  <Map />
  
  <button id="sidebar-toggle" title="Toggle sidebar" onclick={() => $sidebarCollapsed = !$sidebarCollapsed}>☰</button>
</div>

<style>
  /* Mimic the #app layout from the original index */
  .app-container {
    display: flex;
    height: 100vh;
    width: 100vw;
    overflow: hidden;
  }
</style>
