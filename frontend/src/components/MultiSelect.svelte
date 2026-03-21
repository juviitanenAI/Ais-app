<script>
  import { onMount } from 'svelte';
  import { filterCategories as filterStore } from '../lib/stores.js';

  export let categories = []; // Array of {name, color}
  export let onSelectionChange = () => {};

  let isOpen = false;
  let dropdownRef;

  function toggleDropdown() {
    isOpen = !isOpen;
  }

  function handleKeydown(e) {
    if (e.key === 'Escape') isOpen = false;
  }

  function handleClickOutside(e) {
    if (isOpen && dropdownRef && !dropdownRef.contains(e.target)) {
      isOpen = false;
    }
  }

  function toggleCategory(name) {
    filterStore.update(current => {
      const next = current.includes(name)
        ? current.filter(c => c !== name)
        : [...current, name];
      onSelectionChange(next);
      return next;
    });
  }

  function selectAll() {
    const all = categories.map(c => c.name);
    filterStore.set(all);
    onSelectionChange(all);
  }

  function clearAll() {
    filterStore.set([]);
    onSelectionChange([]);
  }

  $: label = $filterStore.length === 0 
    ? 'All Vessel Types' 
    : ($filterStore.length === categories.length 
        ? 'All Vessel Types' 
        : ($filterStore.length === 1 ? $filterStore[0] : `${$filterStore.length} Types`));

</script>

<svelte:window onkeydown={handleKeydown} onclick={handleClickOutside} />

<div class="multiselect" bind:this={dropdownRef}>
  <button class="multiselect-btn" onclick={toggleDropdown} class:active={isOpen}>
    <span class="btn-text">{label}</span>
    <span class="chevron" class:open={isOpen}>▼</span>
  </button>

  {#if isOpen}
    <div class="multiselect-dropdown">
      <div class="dropdown-actions">
        <button onclick={selectAll}>Select All</button>
        <button onclick={clearAll}>Clear All</button>
      </div>
      <div class="options-list">
        {#each categories as cat}
          <!-- svelte-ignore a11y_click_events_have_key_events -->
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div class="option" onclick={() => toggleCategory(cat.name)}>
            <input type="checkbox" checked={$filterStore.includes(cat.name)} readonly />
            <div class="legend-dot" style="background: {cat.color}"></div>
            <span class="option-label">{cat.name.charAt(0).toUpperCase() + cat.name.slice(1)}</span>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .multiselect {
    position: relative;
    width: 100%;
  }

  .multiselect-btn {
    width: 100%;
    padding: 8px 12px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text-primary);
    font-size: 12px;
    font-family: inherit;
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    transition: all 0.2s;
  }

  .multiselect-btn:hover, .multiselect-btn.active {
    border-color: var(--accent);
  }

  .chevron {
    font-size: 10px;
    color: var(--text-secondary);
    transition: transform 0.2s;
  }

  .chevron.open {
    transform: rotate(180deg);
  }

  .multiselect-dropdown {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    z-index: 1100;
    max-height: 300px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .dropdown-actions {
    display: flex;
    padding: 8px;
    gap: 8px;
    border-bottom: 1px solid var(--border);
  }

  .dropdown-actions button {
    flex: 1;
    padding: 4px;
    font-size: 10px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text-secondary);
    cursor: pointer;
  }

  .dropdown-actions button:hover {
    color: var(--text-primary);
    border-color: var(--accent);
  }

  .options-list {
    overflow-y: auto;
    padding: 4px 0;
  }

  .option {
    display: flex;
    align-items: center;
    padding: 8px 12px;
    gap: 10px;
    cursor: pointer;
    transition: background 0.15s;
  }

  .option:hover {
    background: var(--bg-hover);
  }

  .option input {
    margin: 0;
    cursor: pointer;
    pointer-events: none;
  }

  .legend-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .option-label {
    font-size: 12px;
    color: var(--text-primary);
    text-transform: capitalize;
  }
</style>
