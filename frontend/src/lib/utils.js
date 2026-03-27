import { get } from 'svelte/store';
import { vesselTypeCache } from './stores.js';

export function vesselTypeInfo(typeCode, vtypeInfo = null) {
  if (vtypeInfo && vtypeInfo.color) {
    return { 
      label: vtypeInfo.label || 'Unknown', 
      color: vtypeInfo.color, 
      category: vtypeInfo.category || 'other' 
    };
  }

  const cache = get(vesselTypeCache);
  const codeStr = String(typeCode);
  if (cache && cache[codeStr]) {
    const cached = cache[codeStr];
    return {
      label: cached.desc_en || cached.desc_fi || 'Other',
      color: cached.color || '#8899aa',
      category: cached.category || 'other'
    };
  }

  if (!typeCode) return { label: 'Unknown', color: '#8899aa', category: 'other' };
  return { label: 'Other', color: '#8899aa', category: 'other' };
}

export function createShipSvg(color, heading, isPinned = false, isActive = false) {
  const rot = (typeof heading === 'number' && heading < 360) ? heading : 0;
  const classes = ['ship-icon'];
  if (isPinned) classes.push('pinned');
  if (isActive) classes.push('active');
  
  return `<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"
    class="${classes.join(' ')}" style="transform:rotate(${rot}deg)${isActive ? ' scale(1.2)' : ''}; transform-origin: center;">
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

export function createBuoySvg(isActive = false) {
  const classes = ['buoy-icon'];
  if (isActive) classes.push('active');
  
  return `<svg width="20" height="20" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"
    class="${classes.join(' ')}" style="${isActive ? 'transform: scale(1.3);' : ''} transform-origin: center;">
    <circle cx="12" cy="12" r="8" fill="#ffcc00" stroke="#333" stroke-width="2" />
    <path d="M12 4V20M4 12H20" stroke="#333" stroke-width="1.5" opacity="0.6"/>
  </svg>`;
}

export function buoyIcon(isActive = false) {
  return L.divIcon({
    html: createBuoySvg(isActive),
    className: 'buoy-marker-container',
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });
}

export function compareVessels(a, b, selectedMmsis, activeMmsi) {
  const isASelected = selectedMmsis.has(a.mmsi) || a.mmsi === activeMmsi;
  const isBSelected = selectedMmsis.has(b.mmsi) || b.mmsi === activeMmsi;
  
  if (isASelected && !isBSelected) return -1;
  if (!isASelected && isBSelected) return 1;
  
  const na = (a.name || 'zzz').toLowerCase();
  const nb = (b.name || 'zzz').toLowerCase();
  return na.localeCompare(nb);
}

export function filterVessels(vess, searchVal) {
  if (!searchVal) return vess;
  const search = searchVal.toLowerCase();
  return vess.filter(v => 
    (v.name || '').toLowerCase().includes(search) || v.mmsi.toString().includes(search)
  );
}
