<script>
  import { onMount, setContext } from 'svelte';
  import Sidebar from './components/Sidebar.svelte';
  import Map from './components/Map.svelte';
  import LoadingOverlay from './components/LoadingOverlay.svelte';
  import { sidebarCollapsed, isLoading, activeMmsi, activeBuoySite } from './lib/stores.js';
  import { fetchVesselTypes, fetchLiveVesselData, fetchSearchResults, fetchBuoys } from './lib/api.js';
  import { connectWebSocket } from './lib/ws.js';
  import { addOrUpdateVessel, addOrUpdateBuoy, map as leafMap, setAutoFollow, focusOnBuoy } from './lib/map.js';
  import { vessels as vesselsStore, buoys as buoysStore } from './lib/stores.js';
  import { vesselTypeInfo, shipIcon } from './lib/utils.js';
  import { get } from 'svelte/store';

  function handleSelectVessel(mmsi) {
    activeMmsi.set(mmsi);
    activeBuoySite.set(null); // Clear buoy selection when selecting vessel
    setAutoFollow(true);
    sidebarCollapsed.set(false);
  }

  function handleFocusOnBuoy(buoy) {
    focusOnBuoy(buoy);
    activeMmsi.set(null);
    sidebarCollapsed.set(false);
  }

  setContext('mapActions', {
    focusOnBuoy: handleFocusOnBuoy
  });

  onMount(async () => {
    try {
      // Parallel fetch: vessel types, live data, and buoys
      const [_, data, bData] = await Promise.all([
        fetchVesselTypes(),
        fetchLiveVesselData(),
        fetchBuoys()
      ]);
      
      // Batch initial vessel load
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

      // Load initial buoys
      buoysStore.set(bData);
      bData.forEach(b => {
        addOrUpdateBuoy(b);
      });
      
      isLoading.set(false);
    } catch (e) {
      console.error('[load] Failed to initial fetch:', e);
      setTimeout(() => isLoading.set(false), 2000);
    }

    // Start WS and search in parallel
    connectWebSocket(handleSelectVessel);
    fetchSearchResults();
  });
</script>

<LoadingOverlay />

<div class="app-container" class:sidebar-visible={!$sidebarCollapsed}>
  <Sidebar />
  <Map />
</div>

<style>
  .app-container {
    display: flex;
    height: 100vh;
    height: 100dvh;
    width: 100vw;
    overflow: hidden;
  }
</style>
