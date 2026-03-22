<script>
  import { showStatsOverlay, historyMinutes } from '../lib/stores.js';
  import { Line, Doughnut } from 'svelte-chartjs';
  import {
    Chart as ChartJS,
    Title,
    Tooltip,
    Legend,
    LineElement,
    LinearScale,
    PointElement,
    CategoryScale,
    ArcElement,
    Filler
  } from 'chart.js';
  import HistoryToggle from './HistoryToggle.svelte';

  ChartJS.register(
    Title,
    Tooltip,
    Legend,
    LineElement,
    LinearScale,
    PointElement,
    CategoryScale,
    ArcElement,
    Filler
  );

  let timelineData = { labels: [], datasets: [] };
  let categoryData = { labels: [], datasets: [] };
  let loading = false;

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom', labels: { color: '#ccc' } }
    },
    scales: {
      x: { ticks: { color: '#888' }, grid: { color: '#333' } },
      y: { ticks: { color: '#888' }, grid: { color: '#333' } }
    }
  };

  const pieOptions = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: { position: 'right', labels: { color: '#ccc' } }
    }
  };

  async function fetchStats(minutes) {
    loading = true;
    try {
      const res = await fetch(`/api/stats/activity?minutes=${minutes}`);
      const data = await res.json();
      
      const labels = data.timeline.map(d => {
        const date = new Date(d.ts * 1000);
        return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
      });
      const values = data.timeline.map(d => d.count);
      
      timelineData = {
        labels,
        datasets: [
          {
            label: 'Active Vessels',
            data: values,
            borderColor: '#4a9eff',
            backgroundColor: 'rgba(74, 158, 255, 0.2)',
            tension: 0.3,
            fill: true
          }
        ]
      };

      const catLabels = data.categories.map(c => c.category);
      const catValues = data.categories.map(c => c.count);
      const catColors = data.categories.map(c => c.color);

      categoryData = {
        labels: catLabels,
        datasets: [
          {
            data: catValues,
            backgroundColor: catColors,
            borderWidth: 0
          }
        ]
      };

    } catch (e) {
      console.error('Failed to fetch stats', e);
    } finally {
      loading = false;
    }
  }

  $: {
    if ($showStatsOverlay) {
      fetchStats($historyMinutes);
    }
  }

  function closeOverlay() {
    showStatsOverlay.set(false);
  }
</script>

{#if $showStatsOverlay}
  <div class="stats-overlay-container" role="presentation" onpointerdown={closeOverlay}>
    <div class="stats-modal" role="dialog" aria-modal="true" tabindex="-1" onpointerdown={(e) => e.stopPropagation()}>
      <div class="stats-header">
        <h2>Vessel Activity Trends</h2>
        <button class="close-btn" onclick={closeOverlay}>×</button>
      </div>
      
      <div class="stats-controls">
        <span class="control-label">Time Window:</span>
        <HistoryToggle forceHeatmapOptions={true} />
      </div>

      {#if loading}
        <div class="loading">Loading stats...</div>
      {:else}
        <div class="charts-container">
          <div class="chart-box line-chart">
            <h3>Active Vessels Over Time</h3>
            <div class="chart-wrapper">
              <Line data={timelineData} options={chartOptions} />
            </div>
          </div>
          
          <div class="chart-box pie-chart">
            <h3>Category Distribution</h3>
            <div class="chart-wrapper">
              <Doughnut data={categoryData} options={pieOptions} />
            </div>
          </div>
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
  .stats-overlay-container {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.6);
    z-index: 10000;
    display: flex;
    justify-content: center;
    align-items: center;
  }
  .stats-modal {
    background: var(--bg-secondary, #1a1a1a);
    border: 1px solid var(--border-color, #333);
    border-radius: 8px;
    width: 90%;
    max-width: 800px;
    height: 85%;
    max-height: 700px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    color: var(--text-color, #fff);
    padding: 20px;
    box-sizing: border-box;
  }
  .stats-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border-color, #333);
    padding-bottom: 15px;
    margin-bottom: 20px;
  }
  .stats-header h2 {
    margin: 0;
    font-size: 1.3rem;
  }
  .close-btn {
    background: none;
    border: none;
    color: var(--text-muted, #888);
    font-size: 2rem;
    cursor: pointer;
    line-height: 1;
    padding: 0;
  }
  .close-btn:hover {
    color: #fff;
  }
  .stats-controls {
    display: flex;
    align-items: center;
    gap: 15px;
    margin-bottom: 20px;
    background: rgba(0,0,0,0.2);
    padding: 10px;
    border-radius: 6px;
  }
  .stats-controls .control-label {
    font-size: 0.9rem;
    color: var(--text-muted, #aaa);
    white-space: nowrap;
  }
  .charts-container {
    display: flex;
    flex-direction: column;
    gap: 20px;
    flex-grow: 1;
    overflow-y: auto;
  }
  .chart-box {
    background: rgba(255,255,255,0.03);
    border: 1px solid var(--border-color, #333);
    border-radius: 6px;
    padding: 15px;
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 250px;
    overflow: hidden;
  }
  .chart-box h3 {
    margin: 0 0 15px 0;
    font-size: 1.1rem;
    color: #ccc;
    text-align: center;
  }
  .chart-wrapper {
    position: relative;
    flex-grow: 1;
    min-height: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .loading {
    display: flex;
    justify-content: center;
    align-items: center;
    flex-grow: 1;
    color: var(--text-muted, #888);
    font-size: 1.2rem;
  }
</style>
