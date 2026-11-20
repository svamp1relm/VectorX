<script setup lang="ts">
import { Chart, type ChartConfiguration } from 'chart.js/auto'
import { onMounted, onUnmounted, ref, watch } from 'vue'
import type { EquityPoint } from '../types'
import { usePreferences } from '../preferences'

const props = defineProps<{ points: EquityPoint[] }>()
const { locale, theme, t } = usePreferences()

const canvasRef = ref<HTMLCanvasElement | null>(null)
let chart: InstanceType<typeof Chart> | null = null

function textColor(): string {
  return getComputedStyle(document.documentElement).getPropertyValue('--text').trim() || '#17212b'
}

function buildConfig(points: EquityPoint[]): ChartConfiguration {
  const color = textColor()
  return {
    type: 'line',
    data: {
      labels: points.map((point) => point.index),
      datasets: [
        {
          label: t('charts.equity'),
          data: points.map((point) => point.equity),
          borderColor: '#42b883',
          pointRadius: 0,
        },
      ],
    },
    options: {
      responsive: true,
      animation: false,
      plugins: { legend: { labels: { color } } },
      scales: { x: { ticks: { color } }, y: { ticks: { color } } },
    },
  }
}

function render(points: EquityPoint[]) {
  if (!canvasRef.value) return
  chart?.destroy()
  chart = new Chart(canvasRef.value, buildConfig(points))
}

onMounted(() => render(props.points))
watch(() => props.points, render)
watch([locale, theme], () => render(props.points))
onUnmounted(() => chart?.destroy())
</script>

<template>
  <canvas ref="canvasRef" role="img" :aria-label="t('charts.equity')"></canvas>
  <details class="chart-data">
    <summary>{{ t('charts.data') }}</summary>
    <table>
      <thead><tr><th>{{ t('runs.run') }}</th><th>{{ t('charts.equity') }}</th><th>{{ t('runs.maxDrawdown') }}</th></tr></thead>
      <tbody>
        <tr v-for="point in points" :key="point.index">
          <td>{{ point.index }}</td><td>{{ point.equity }}</td><td>{{ point.drawdown }}</td>
        </tr>
      </tbody>
    </table>
  </details>
</template>
