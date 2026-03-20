export const state = {
  vessels: {},         // mmsi -> { marker, data, lastUpdate }
  selectedMmsi: null,
  selectionRing: null,   // Leaflet marker for the pulsing ring
  historyPolyline: null,
  historyMinutes: 180,
  historyPollTimer: null,
  ws: null,
  wsReconnectTimer: null,
  currentSearchResults: [],
  listUpdateTimer: null
};
