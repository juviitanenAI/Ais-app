<script>
  import { isLoading, isBackendReady } from '../lib/stores.js';
</script>

<div id="loading-overlay" class:hidden={!$isLoading}>
  <div class="loader">
    <div class="loader-spinner"></div>
    <div class="loader-text">
      {#if !$isBackendReady}
        Connecting to maritime backend…
      {:else}
        Loading vessel data…
      {/if}
    </div>
  </div>
</div>
