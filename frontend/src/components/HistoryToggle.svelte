<script>
  import { heatmapMode, historyMinutes } from '../lib/stores.js';

  const normalOptions = [
    { label: '1h', value: 60 },
    { label: '3h', value: 180 },
    { label: '12h', value: 720 },
    { label: '24h', value: 1440 }
  ];

  const heatmapOptions = [
    { label: '12h', value: 720 },
    { label: '24h', value: 1440 },
    { label: '3 days', value: 4320 },
    { label: '1 wk', value: 10080 }
  ];

  export let forceHeatmapOptions = false;

  $: options = (forceHeatmapOptions || $heatmapMode) ? heatmapOptions : normalOptions;

  function setHistory(min) {
    historyMinutes.set(min);
  }
</script>

<div class="history-controls">
  {#each options as option}
    <button 
      class="history-btn" 
      class:active={$historyMinutes === option.value} 
      onclick={() => setHistory(option.value)}
    >
      {option.label}
    </button>
  {/each}
</div>
