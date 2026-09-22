<script setup lang="ts">
import type { RunResult } from '../types'

defineProps<{ results: RunResult[] }>()
</script>

<template>
  <p v-if="results.length === 0">No runs.</p>
  <table v-else>
    <thead>
      <tr>
        <th>Run</th>
        <th>Win rate</th>
        <th>Expectancy (sample)</th>
        <th>Total return</th>
        <th>Max drawdown</th>
        <th>Profit factor</th>
        <th>Ruined</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="run in results" :key="run.run_index">
        <td>{{ run.run_index }}</td>
        <td>{{ run.metrics.win_rate }}</td>
        <td>{{ run.metrics.expectancy_sample }}</td>
        <td>{{ run.metrics.total_return }}</td>
        <td>{{ run.metrics.max_drawdown }}</td>
        <td>{{ run.metrics.profit_factor }}</td>
        <td>{{ run.metrics.ruined }}</td>
      </tr>
    </tbody>
  </table>
</template>
