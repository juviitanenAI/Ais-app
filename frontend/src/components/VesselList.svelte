<script>
  import { get } from 'svelte/store';
  import { vessels, currentSearchResults, activeMmsi, selectedMmsis, heatmapMode, filterCategories, hideOthers } from '../lib/stores.js';
  import { filterVessels, compareVessels, vesselTypeInfo } from '../lib/utils.js';

  export let searchTerm = '';

  let sortedVessels = [];

  // Reactive logic to combine and sort
  $: {
    const combined = new Map();
    const liveVessels = $vessels;
    
    // Add search results
    for (const res of $currentSearchResults) {
      combined.set(res.mmsi, { mmsi: res.mmsi, name: res.name, is_live: res.is_live, latest_ts: res.latest_ts });
    }

    for (const [mmsi, v] of Object.entries(liveVessels)) {
      const isPinned = $selectedMmsis.has(mmsi) || mmsi === $activeMmsi;
      
      if ($hideOthers && !isPinned) continue;

      if ($filterCategories.length > 0 && !isPinned) {
        const liveCat = v.data.vtype_info?.category?.toLowerCase() || 'other';
        if (!$filterCategories.includes(liveCat)) continue;
      }
      
      if (!combined.has(mmsi)) {
        combined.set(mmsi, { mmsi, name: v.data.name, is_live: true, latest_ts: Math.floor(v.lastUpdate / 1000) });
      } else {
        const item = combined.get(mmsi);
        item.is_live = true;
        item.latest_ts = Math.max(item.latest_ts || 0, Math.floor(v.lastUpdate / 1000));
      }
    }

    const filtered = filterVessels(Array.from(combined.values()), searchTerm);
    sortedVessels = filtered.sort((a, b) => compareVessels(a, b, $selectedMmsis, $activeMmsi)).slice(0, 200);
  }

  function togglePin(mmsi, event) {
    // We update the Set reference to trigger reactivity
    const newSet = new Set($selectedMmsis);
    if (event.target.checked) {
      newSet.add(mmsi);
    } else {
      newSet.delete(mmsi);
    }
    selectedMmsis.set(newSet);
  }

  function selectShip(mmsi) {
    if ($heatmapMode) return;
    if ($activeMmsi === mmsi) {
      activeMmsi.set(null);
    } else {
      activeMmsi.set(mmsi);
    }
  }

  function getSpeed(mmsi) {
    const d = $vessels[mmsi]?.data;
    return d && d.sog != null ? d.sog.toFixed(1) + ' kn' : '';
  }

  function getTimeStr(ts) {
    if (!ts) return 'Unknown';
    const d = new Date(ts * 1000);
    return d.toLocaleString('fi-FI', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit'});
  }
</script>

<div class="vessel-list" id="vessel-list">
  {#if sortedVessels.length === 0}
    <div style="padding:20px 16px; text-align:center; color:var(--text-muted); font-size:13px;">No vessels found</div>
  {/if}

  {#each sortedVessels as v (v.mmsi)}
    {@const typeObj = vesselTypeInfo($vessels[v.mmsi]?.data?.type, $vessels[v.mmsi]?.data?.vtype_info)}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div 
      class="vessel-item {$heatmapMode ? '' : (v.mmsi === $activeMmsi ? 'active' : '')}" 
      onclick={(e) => { if (!e.target.classList.contains('vessel-pin')) selectShip(v.mmsi); }}
    >
      <input type="checkbox" class="vessel-pin" 
        checked={$selectedMmsis.has(v.mmsi)} 
        style="{$heatmapMode ? 'display:none' : ''}"
        onchange={(e) => togglePin(v.mmsi, e)}
        title="Pin track to map">
      
      <!-- dot logic -->
      <div class="vessel-dot" style={v.is_live ? `background:${typeObj.color}; box-shadow: 0 0 4px ${typeObj.color};` : 'background:var(--text-muted); opacity:0.5;'}></div>
      
      <div class="vessel-info">
        <div class="vessel-name">{v.name || '(Unknown)'}</div>
        <div class="vessel-mmsi">{v.mmsi} <span style="font-size: 9px; color: var(--text-muted); margin-left: 6px;">Latest: {getTimeStr(v.latest_ts)}</span></div>
      </div>
      <div class="vessel-speed">{getSpeed(v.mmsi)}</div>
    </div>
  {/each}
</div>
