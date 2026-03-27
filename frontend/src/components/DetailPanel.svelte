<script>
  import { vessels, activeMmsi, currentSearchResults, autoFollow, buoys, activeBuoySite } from '../lib/stores.js';
  import { vesselTypeInfo, formatDate } from '../lib/utils.js';
  import { setAutoFollow } from '../lib/map.js';

  let mmsi = null;
  let siteNum = null;
  let name = '(Unknown)', typeLab = 'Unknown', typeCol = '#8899aa';
  let speed = '—', hdg = '—', cog = '—', dest = '—', imo = null;
  let temp = '—', seaState = '—', trend = '';
  let updatedAt = '—';

  $: isBuoy = $activeBuoySite !== null;
  $: isVessel = $activeMmsi !== null;

  $: {
    if ($activeMmsi) {
      mmsi = $activeMmsi;
      const v = $vessels[mmsi];
      if (v) {
        const d = v.data;
        const ti = vesselTypeInfo(d.type, d.vtype_info);
        name = d.name || '(Unknown)';
        typeLab = ti.label; typeCol = ti.color;
        speed = (d.sog != null) ? d.sog.toFixed(1) + ' kn' : '—';
        hdg = (d.heading != null) ? d.heading.toFixed(0) + '°' : '—';
        cog = (d.cog != null) ? d.cog.toFixed(0) + '°' : '—';
        dest = d.destination || '—';
        imo = d.imo;
        updatedAt = formatDate(d.lastSeen || v.lastUpdate);
      } else {
        const match = $currentSearchResults.find(r => r.mmsi === mmsi);
        if (match) name = match.name || '(Unknown)';
      }
    } else if ($activeBuoySite) {
      siteNum = $activeBuoySite;
      const b = $buoys.find(buoy => buoy.data.siteNumber === siteNum);
      if (b) {
        const d = b.data;
        name = d.siteName || '(Unknown Site)';
        typeLab = d.siteType || 'Buoy';
        typeCol = '#ffcc00'; // Buoy yellow
        temp = d.temperature !== null ? d.temperature + ' °C' : '—';
        seaState = d.seaState || '—';
        trend = d.trend || '';
        updatedAt = formatDate(b.dataUpdatedTime);
      }
    }
  }

  function handleClose() {
    activeMmsi.set(null);
    activeBuoySite.set(null);
    autoFollow.set(false);
  }

  function toggleFollow() {
    setAutoFollow(!$autoFollow);
  }
</script>

<div class="detail-panel" class:visible={isVessel || isBuoy}>
  <div class="detail-header">
    <div class="detail-name-row">
      <span class="detail-name">{name}</span>
      {#if isVessel}
        <button 
          class="detail-follow-btn" 
          class:active={$autoFollow}
          onclick={toggleFollow}
          title={$autoFollow ? "Following - click to stop" : "Not following - click to follow"}
        >
          {$autoFollow ? '📍 Following' : '🛰️ Follow'}
        </button>
      {/if}
    </div>
    <button class="detail-close" onclick={handleClose}>✕</button>
  </div>
  
  <div class="detail-grid">
    {#if isVessel}
      <div class="detail-field"><div class="detail-label">MMSI</div><div class="detail-value">{mmsi}</div></div>
      <div class="detail-field"><div class="detail-label">Type</div><div class="detail-value" style="color:{typeCol}">{typeLab}</div></div>
      <div class="detail-field"><div class="detail-label">Speed</div><div class="detail-value">{speed}</div></div>
      <div class="detail-field"><div class="detail-label">Heading</div><div class="detail-value">{hdg}</div></div>
      <div class="detail-field"><div class="detail-label">Course</div><div class="detail-value">{cog}</div></div>
      <div class="detail-field"><div class="detail-label">Destination</div><div class="detail-value">{dest}</div></div>
      {#if imo}
        <div class="detail-field"><div class="detail-label">IMO</div><div class="detail-value">{imo}</div></div>
        <div class="detail-field">
          <div class="detail-label">External Info</div>
          <div class="detail-value">
            <a href="https://www.marinetraffic.com/ais/details/ships/imo:{imo}" 
               target="_blank" 
               rel="noopener noreferrer" 
               class="mt-link" 
               title="View on MarineTraffic">
               MarineTraffic ↗️
            </a>
          </div>
        </div>
      {/if}
    {:else if isBuoy}
      <div class="detail-field"><div class="detail-label">Site #</div><div class="detail-value">{siteNum}</div></div>
      <div class="detail-field"><div class="detail-label">Type</div><div class="detail-value" style="color:{typeCol}">{typeLab}</div></div>
      <div class="detail-field"><div class="detail-label">Temperature</div><div class="detail-value">{temp}</div></div>
      <div class="detail-field"><div class="detail-label">Sea State</div><div class="detail-value">{seaState} {trend ? '(' + trend + ')' : ''}</div></div>
    {/if}
    <div class="detail-field" style="grid-column: span 2;">
      <div class="detail-label">Last Update</div>
      <div class="detail-value">{updatedAt}</div>
    </div>
  </div>
</div>
