import { APP_VERSION, STALE_MINUTES } from './config.js';
import { fetchLiveVesselData, fetchSearchResults, fetchVesselTypes } from './api.js';
import { connectWebSocket } from './ws.js';
import { addOrUpdateVessel, pruneStaleVessels } from './map.js';
import { updateVesselCount, updateVesselList, initUIListeners } from './ui.js';

document.querySelectorAll('.app-version').forEach(el => el.textContent = APP_VERSION);

setInterval(() => pruneStaleVessels(STALE_MINUTES), 60000);

initUIListeners();

async function init() {
  try {
    await fetchVesselTypes();
    const data = await fetchLiveVesselData();
    data.forEach(v => addOrUpdateVessel(v));
    updateVesselCount();
    
    await fetchSearchResults();
    updateVesselList();

    document.getElementById('loading-overlay').classList.add('hidden');
  } catch (e) {
    console.error('[load] Failed to fetch live vessels:', e);
    setTimeout(() => {
      document.getElementById('loading-overlay').classList.add('hidden');
    }, 2000);
  }

  connectWebSocket();
}

init();

setTimeout(() => {
  document.getElementById('loading-overlay').classList.add('hidden');
}, 5000);