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
  listUpdateTimer: null,
  vessel_type_cache: {}  // code -> { color, desc_fi, desc_en, category }
};
