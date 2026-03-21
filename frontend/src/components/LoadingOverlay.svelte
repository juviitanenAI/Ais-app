<script>
  import { isLoading } from '../lib/stores.js';
</script>

<div id="loading-overlay" class:hidden={!$isLoading}>
  <div class="loader">
    <div class="loader-spinner"></div>
    <div class="loader-text">Connecting to AIS feed…</div>
  </div>
</div>
