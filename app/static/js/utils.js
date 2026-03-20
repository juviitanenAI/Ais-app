import { state } from './state.js';

export function vesselTypeInfo(typeCode, vtypeInfo = null) {
  // 1. If we have direct info passed, use it
  if (vtypeInfo && vtypeInfo.color) {
    return { 
      label: vtypeInfo.label || 'Unknown', 
      color: vtypeInfo.color, 
      category: vtypeInfo.category || 'other' 
    };
  }

  // 2. Fallback to global cache if available
  const codeStr = String(typeCode);
  if (state.vessel_type_cache && state.vessel_type_cache[codeStr]) {
    const cached = state.vessel_type_cache[codeStr];
    return {
      label: cached.desc_en || cached.desc_fi || 'Other',
      color: cached.color || '#8899aa',
      category: cached.category || 'other'
    };
  }

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

export function createShipSvg(color, heading, isPinned = false, isActive = false) {
  const rot = (typeof heading === 'number' && heading < 360) ? heading : 0;
  const classes = ['ship-icon'];
  if (isPinned) classes.push('pinned');
  if (isActive) classes.push('active');
  
  return `<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"
    class="${classes.join(' ')}" style="transform:rotate(${rot}deg)">
    <polygon points="12,2 20,20 12,16 4,20" fill="${color}" stroke="rgba(0,0,0,0.6)"
      stroke-width="1.2" opacity="0.95"/>
  </svg>`;
}

export function shipIcon(color, heading, isPinned = false, isActive = false) {
  return L.divIcon({
    html: createShipSvg(color, heading, isPinned, isActive),
    className: 'vessel-marker-container',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });
}
