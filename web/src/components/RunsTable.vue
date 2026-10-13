<script setup lang="ts">
import { usePreferences } from '../preferences'
import type { RunResult } from '../types'

defineProps<{ results: RunResult[] }>()
const { t } = usePreferences()
</script>

<template>
  <p v-if="results.length === 0">{{ t('state.noRuns') }}</p>
  <table v-else>
    <thead>
      <tr>
        <th>{{ t('runs.run') }}</th>
        <th>{{ t('runs.trades') }}</th>
        <th>{{ t('runs.winRate') }}</th>
        <th>{{ t('runs.expectancy') }}</th>
        <th>{{ t('runs.totalReturn') }}</th>
        <th>{{ t('runs.maxDrawdown') }}</th>
        <th>{{ t('runs.profitFactor') }}</th>
        <th>{{ t('runs.ruined') }}</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="run in results" :key="run.run_index">
        <td>{{ run.run_index }}</td>
        <td>{{ run.metrics.trades }}</td>
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
