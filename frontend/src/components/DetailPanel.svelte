<script>
  import { vessels, activeMmsi, currentSearchResults, historyMinutes } from '../lib/stores.js';
  import { vesselTypeInfo } from '../lib/utils.js';
  import HistoryToggle from './HistoryToggle.svelte';

  let mmsi = null;
  let name = '(Unknown)', typeLab = 'Unknown', typeCol = '#8899aa';
  let speed = '—', hdg = '—', cog = '—', dest = '—';

  $: {
    mmsi = $activeMmsi;
    if (mmsi) {
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
      } else {
        const match = $currentSearchResults.find(r => r.mmsi === mmsi);
        if (match) name = match.name || '(Unknown)';
      }
    }
  }

</script>

<div class="detail-panel" class:visible={$activeMmsi !== null}>
  <div class="detail-header">
    <span class="detail-name">{name}</span>
    <button class="detail-close" onclick={() => activeMmsi.set(null)}>✕</button>
  </div>
  
  <div class="detail-grid">
    <div class="detail-field"><div class="detail-label">MMSI</div><div class="detail-value">{mmsi}</div></div>
    <div class="detail-field"><div class="detail-label">Type</div><div class="detail-value" style="color:{typeCol}">{typeLab}</div></div>
    <div class="detail-field"><div class="detail-label">Speed</div><div class="detail-value">{speed}</div></div>
    <div class="detail-field"><div class="detail-label">Heading</div><div class="detail-value">{hdg}</div></div>
    <div class="detail-field"><div class="detail-label">Course</div><div class="detail-value">{cog}</div></div>
    <div class="detail-field"><div class="detail-label">Destination</div><div class="detail-value">{dest}</div></div>
  </div>
  
  <div class="detail-history-controls">
    <HistoryToggle />
  </div>
</div>
