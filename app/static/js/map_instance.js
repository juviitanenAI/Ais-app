export const map = L.map('map', {
  zoomControl: false,
  attributionControl: true,
  preferCanvas: true, // Use Canvas renderer for better performance with many points
}).setView([60.5, 22.0], 7);
