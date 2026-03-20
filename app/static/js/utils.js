export function vesselTypeInfo(typeCode) {
  // AIS ship type codes: https://coast.noaa.gov/data/marinecadastre/ais/VesselTypeCodes2018.pdf
  if (!typeCode) return { label: 'Unknown', color: '#8899aa', category: 'other' };
  const t = parseInt(typeCode);
  if (t >= 70 && t <= 79) return { label: 'Cargo', color: '#4a9eff', category: 'cargo' };
  if (t >= 80 && t <= 89) return { label: 'Tanker', color: '#ff6b6b', category: 'tanker' };
  if (t >= 60 && t <= 69) return { label: 'Passenger', color: '#2ed573', category: 'passenger' };
  if (t === 30)           return { label: 'Fishing', color: '#ffa502', category: 'fishing' };
  if (t >= 40 && t <= 49) return { label: 'High Speed', color: '#a29bfe', category: 'other' };
  if (t >= 20 && t <= 29) return { label: 'WIG', color: '#a29bfe', category: 'other' };
  if (t >= 31 && t <= 32) return { label: 'Towing', color: '#dfe6e9', category: 'other' };
  if (t === 36)           return { label: 'Sailing', color: '#74b9ff', category: 'other' };
  if (t === 37)           return { label: 'Pleasure', color: '#fd79a8', category: 'other' };
  return { label: 'Other', color: '#8899aa', category: 'other' };
}

export function createShipSvg(color, heading) {
  const rot = (typeof heading === 'number' && heading < 360) ? heading : 0;
  return `<svg width="20" height="20" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"
    class="ship-icon" style="transform:rotate(${rot}deg)">
    <polygon points="10,1 17,17 10,14 3,17" fill="${color}" stroke="rgba(0,0,0,0.4)"
      stroke-width="0.8" opacity="0.9"/>
  </svg>`;
}

export function shipIcon(color, heading) {
  return L.divIcon({
    html: createShipSvg(color, heading),
    className: '',
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });
}
