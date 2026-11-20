<script setup lang="ts">
import { Chart, type ChartConfiguration } from 'chart.js/auto'
import { onMounted, onUnmounted, ref, watch } from 'vue'
import type { HistogramBins } from '../types'
import { usePreferences } from '../preferences'

const props = defineProps<{ bins: HistogramBins }>()
const { theme, t } = usePreferences()

const canvasRef = ref<HTMLCanvasElement | null>(null)
let chart: InstanceType<typeof Chart> | null = null

function binLabels(bins: HistogramBins): string[] {
  const labels: string[] = []
  for (let i = 0; i < bins.counts.length; i++) {
    const midpoint = (bins.edges[i] + bins.edges[i + 1]) / 2
    labels.push(midpoint.toFixed(3))
  }
  return labels
}

function textColor(): string {
  return getComputedStyle(document.documentElement).getPropertyValue('--text').trim() || '#17212b'
}

function buildConfig(bins: HistogramBins): ChartConfiguration {
  const color = textColor()
  return {
    type: 'bar',
    data: {
      labels: binLabels(bins),
      datasets: [{ label: t('charts.count'), data: bins.counts, backgroundColor: '#42b883' }],
    },
    options: {
      responsive: true,
      animation: false,
      plugins: { legend: { labels: { color } } },
      scales: { x: { ticks: { color } }, y: { ticks: { color } } },
    },
  }
}

function render(bins: HistogramBins) {
  if (!canvasRef.value) return
  chart?.destroy()
  chart = new Chart(canvasRef.value, buildConfig(bins))
}

onMounted(() => render(props.bins))
watch(() => props.bins, render)
watch(theme, () => render(props.bins))
onUnmounted(() => chart?.destroy())
</script>

<template>
  <canvas ref="canvasRef" role="img" :aria-label="t('charts.count')"></canvas>
  <details class="chart-data">
    <summary>{{ t('charts.data') }}</summary>
    <table>
      <thead><tr><th>{{ t('charts.bin') }}</th><th>{{ t('charts.count') }}</th></tr></thead>
      <tbody>
        <tr v-for="(label, index) in binLabels(bins)" :key="label">
          <td>{{ label }}</td><td>{{ bins.counts[index] }}</td>
        </tr>
      </tbody>
    </table>
  </details>
</template>
