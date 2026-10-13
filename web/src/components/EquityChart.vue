<script setup lang="ts">
import { Chart, type ChartConfiguration } from 'chart.js/auto'
import { onMounted, onUnmounted, ref, watch } from 'vue'
import type { EquityPoint } from '../types'
import { usePreferences } from '../preferences'

const props = defineProps<{ points: EquityPoint[] }>()
const { locale, t } = usePreferences()

const canvasRef = ref<HTMLCanvasElement | null>(null)
let chart: InstanceType<typeof Chart> | null = null

function buildConfig(points: EquityPoint[]): ChartConfiguration {
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
    options: { responsive: true, animation: false },
  }
}

function render(points: EquityPoint[]) {
  if (!canvasRef.value) return
  chart?.destroy()
  chart = new Chart(canvasRef.value, buildConfig(points))
}

onMounted(() => render(props.points))
watch(() => props.points, render)
watch(locale, () => render(props.points))
onUnmounted(() => chart?.destroy())
</script>

<template>
  <canvas ref="canvasRef"></canvas>
</template>
