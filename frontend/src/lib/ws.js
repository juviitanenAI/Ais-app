import { get } from 'svelte/store';
import { WS_URL } from './config.js';
import { vessels as vesselsStore, buoys as buoysStore, activeMmsi, wsConnected } from './stores.js';
import { addOrUpdateVessel, addOrUpdateBuoy } from './map.js';
import { fetchBuoys } from './api.js';

let ws = null;
let wsReconnectTimer = null;

export function connectWebSocket(onSelectCallback) {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;

  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    console.log('[ws] Connected');
    wsConnected.set(true);
    ws.send(JSON.stringify({ type: 'subscribe_all' }));
  };

  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.type === 'metadata') {
        vesselsStore.update(vs => {
          const existing = vs[msg.mmsi];
          if (existing) {
            existing.data.name = msg.meta?.name || existing.data.name;
            existing.data.type = msg.meta?.type || existing.data.type;
            existing.data.destination = msg.meta?.destination || existing.data.destination;
            existing.data.imo = msg.meta?.imo || existing.data.imo;
            existing.data.vtype_info = msg.vtype_info || existing.data.vtype_info;
            addOrUpdateVessel(existing.data, onSelectCallback);
          }
          return vs;
        });
        return;
      }

      if (msg.type === 'buoys') {
        console.log(`[ws] Buoys updated: ${msg.dataUpdatedTime}`);
        fetchBuoys().then(bData => {
          buoysStore.set(bData);
          bData.forEach(b => addOrUpdateBuoy(b));
        });
        return;
      }

      if (msg.type !== 'location') return;

      const lat = msg.loc?.lat;
      const lon = msg.loc?.lon;
      if (typeof lat !== 'number' || typeof lon !== 'number') return;

      const vessels = get(vesselsStore);
      const v = {
        mmsi: msg.mmsi,
        name: msg.meta?.name || vessels[msg.mmsi]?.data?.name || '',
        type: msg.meta?.type || vessels[msg.mmsi]?.data?.type,
        vtype_info: msg.vtype_info,
        destination: msg.meta?.destination || vessels[msg.mmsi]?.data?.destination || '',
        lat, lon,
        sog: msg.loc?.sog,
        cog: msg.loc?.cog,
        heading: msg.loc?.heading,
        lastSeen: msg.loc?.time || Date.now() / 1000,
        imo: msg.meta?.imo || vessels[msg.mmsi]?.data?.imo
      };

      addOrUpdateVessel(v, onSelectCallback);

      // UI components (DetailPanel) will react automatically to store changes.
      // Vessel list updates via store subscriptions.
    } catch (e) {
      console.warn('[ws] parse error:', e);
    }
  };

  ws.onerror = (e) => {
    console.error('[ws] error', e);
  };

  ws.onclose = (ev) => {
    console.log('[ws] closed', ev.code);
    wsConnected.set(false);
    
    clearTimeout(wsReconnectTimer);
    wsReconnectTimer = setTimeout(() => connectWebSocket(onSelectCallback), 3000);
  };
}
