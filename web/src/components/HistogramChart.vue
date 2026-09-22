<script setup lang="ts">
import { Chart, type ChartConfiguration } from 'chart.js/auto'
import { onMounted, onUnmounted, ref, watch } from 'vue'
import type { HistogramBins } from '../types'

const props = defineProps<{ bins: HistogramBins }>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
let chart: InstanceType<typeof Chart> | null = null

// One bar per bin; label each bar with its bin's midpoint, since bins.edges
// has one more entry than bins.counts (n+1 edges bound n bins).
function binLabels(bins: HistogramBins): string[] {
  const labels: string[] = []
  for (let i = 0; i < bins.counts.length; i++) {
    const midpoint = (bins.edges[i] + bins.edges[i + 1]) / 2
    labels.push(midpoint.toFixed(3))
  }
  return labels
}

function buildConfig(bins: HistogramBins): ChartConfiguration {
  return {
    type: 'bar',
    data: {
      labels: binLabels(bins),
      datasets: [
        {
          label: 'Count',
          data: bins.counts,
          backgroundColor: '#42b883',
        },
      ],
    },
    options: { responsive: true, animation: false },
  }
}

function render(bins: HistogramBins) {
  if (!canvasRef.value) return
  chart?.destroy()
  chart = new Chart(canvasRef.value, buildConfig(bins))
}

onMounted(() => render(props.bins))
watch(() => props.bins, render)
onUnmounted(() => chart?.destroy())
</script>

<template>
  <canvas ref="canvasRef"></canvas>
</template>
