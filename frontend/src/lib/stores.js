import { writable, derived } from 'svelte/store';

// Global application state
export const vessels = writable({});
export const buoys = writable([]);
export const activeBuoySite = writable(null);
export const vesselTypeCache = writable({});
export const historyDataCache = writable({});

export const activeMmsi = writable(null);
export const selectedMmsis = writable(new Set());
export const heatmapMode = writable(false);
export const heatmapLoading = writable(false);
export const activeTab = writable('vessels'); // 'vessels' or 'stats'
export const showStatsOverlay = writable(false);

export function toggleHeatmapMode(enable) {
  heatmapMode.set(enable);
  if (enable) {
    activeTab.set('heatmap');
  } else {
    activeTab.set('vessels');
  }
}

export function switchSecondaryTab(tab) {
  activeTab.set(tab);
  heatmapMode.set(tab === 'heatmap');
}

export const historyMinutes = writable(60);
export const autoFollow = writable(false);
export const currentSearchResults = writable([]);
export const filterCategories = writable([]);

export const wsConnected = writable(false);
export const isLoading = writable(true);
export const sidebarCollapsed = writable(false);
export const sidebarExpandedAt = writable(0);
export const hideOthers = writable(false);
export const legendCollapsed = writable(false);
// Derived store to centralize filtering logic
export const filteredVessels = derived(
  [vessels, currentSearchResults, selectedMmsis, activeMmsi, filterCategories, hideOthers],
  ([$vessels, $currentSearchResults, $selectedMmsis, $activeMmsi, $filterCategories, $hideOthers]) => {
    
    const combined = new Map();

    // 1. Start with search results
    for (const res of $currentSearchResults) {
      combined.set(res.mmsi, {
        mmsi: res.mmsi,
        name: res.name,
        is_live: res.is_live,
        latest_ts: res.latest_ts,
        category: null
      });
    }

    // 2. Add/Update from live vessels
    for (const [mmsi, v] of Object.entries($vessels)) {
      const category = v.data.vtype_info?.category || 'Other';
      if (!combined.has(mmsi)) {
        combined.set(mmsi, {
          mmsi,
          name: v.data.name,
          is_live: true,
          latest_ts: Math.floor(v.lastUpdate / 1000),
          category: category
        });
      } else {
        const item = combined.get(mmsi);
        item.is_live = true;
        item.name = v.data.name || item.name;
        item.latest_ts = Math.max(item.latest_ts || 0, Math.floor(v.lastUpdate / 1000));
        item.category = category;
      }
    }

    // 3. Apply Filters to the combined list
    const results = [];
    const activeFilters = $filterCategories.map(c => c.toLowerCase());
    
    for (const item of combined.values()) {
      const mmsi = item.mmsi;
      const isPinned = $selectedMmsis.has(mmsi) || mmsi === $activeMmsi;

      // Filter: Hide Others
      if ($hideOthers && !isPinned) continue;

      // Filter: Category
      if (activeFilters.length > 0 && !isPinned) {
        // Strict filtering: if we don't know the category, or it's not in the list, hide it!
        const cat = item.category ? item.category.toLowerCase() : null;
        if (!cat || !activeFilters.includes(cat)) {
          continue;
        }
      }

      results.push(item);
    }

    return results;
  }
);
