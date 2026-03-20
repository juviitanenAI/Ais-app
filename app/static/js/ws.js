import { WS_URL } from './config.js';
import { state } from './state.js';
import { addOrUpdateVessel } from './map.js';
import { updateDetailPanel, scheduleListUpdate } from './ui.js';

export function connectWebSocket() {
  if (state.ws && (state.ws.readyState === WebSocket.OPEN || state.ws.readyState === WebSocket.CONNECTING)) return;

  state.ws = new WebSocket(WS_URL);

  state.ws.onopen = () => {
    console.log('[ws] Connected');
    document.getElementById('ws-status').textContent = 'Live ●';
    document.getElementById('ws-status').style.color = '#2ed573';
    state.ws.send(JSON.stringify({ type: 'subscribe_all' }));
  };

  state.ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.type !== 'location') return;

      const lat = msg.loc?.lat;
      const lon = msg.loc?.lon;
      if (typeof lat !== 'number' || typeof lon !== 'number') return;

      const v = {
        mmsi: msg.mmsi,
        name: msg.meta?.name || state.vessels[msg.mmsi]?.data?.name || '',
        type: msg.meta?.type || state.vessels[msg.mmsi]?.data?.type,
        destination: msg.meta?.destination || state.vessels[msg.mmsi]?.data?.destination || '',
        lat, lon,
        sog: msg.loc?.sog,
        cog: msg.loc?.cog,
        heading: msg.loc?.heading,
      };

      addOrUpdateVessel(v);

      if (msg.mmsi === state.selectedMmsi) {
        updateDetailPanel(msg.mmsi);
      }

      scheduleListUpdate();
    } catch (e) {
      console.warn('[ws] parse error:', e);
    }
  };

  state.ws.onerror = (e) => {
    console.error('[ws] error', e);
  };

  state.ws.onclose = (ev) => {
    console.log('[ws] closed', ev.code);
    document.getElementById('ws-status').textContent = 'Reconnecting…';
    document.getElementById('ws-status').style.color = '#ffa502';
    
    clearTimeout(state.wsReconnectTimer);
    state.wsReconnectTimer = setTimeout(connectWebSocket, 3000);
  };
}
