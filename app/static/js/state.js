export const state = {
  vessels: {},            // mmsi -> { marker, data, lastUpdate }
  activeMmsi: null,       // Ship currently in detail panel
  selectedMmsis: new Set(), // Pinned ships (tracks stay visible)
  selectionRing: null,    // Leaflet marker for the active ship's pulsing ring
  historyLayers: new Map(), // mmsi -> { polyline, circles: [] }
  historyMinutes: 180,
  historyPollTimer: null,
  ws: null,
  wsReconnectTimer: null,
  currentSearchResults: [],
  listUpdateTimer: null,
  vessel_type_cache: {},  // code -> { color, desc_fi, desc_en, category }
  heatmapMode: false,
  heatmapLayer: null
};
