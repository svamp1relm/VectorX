<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listExperiments } from '../api'
import { usePreferences } from '../preferences'
import type { ExperimentSummaryItem } from '../types'

const emit = defineEmits<{ select: [id: number] }>()
const { t } = usePreferences()

const experiments = ref<ExperimentSummaryItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    experiments.value = await listExperiments()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <h2>{{ t('list.title') }}</h2>
    <p v-if="loading">{{ t('state.loading') }}</p>
    <p v-else-if="error">{{ error }}</p>
    <p v-else-if="experiments.length === 0">{{ t('state.noExperiments') }}</p>
    <table v-else>
      <thead>
        <tr>
          <th>{{ t('table.name') }}</th>
          <th>{{ t('table.seed') }}</th>
          <th>{{ t('table.runs') }}</th>
          <th>{{ t('table.status') }}</th>
          <th>{{ t('table.meanReturn') }}</th>
          <th>{{ t('table.negativeProbability') }}</th>
          <th>{{ t('table.ruinedProbability') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="experiment in experiments"
          :key="experiment.id"
          :data-testid="`experiment-row-${experiment.id}`"
          @click="emit('select', experiment.id)"
        >
          <td>{{ experiment.name }}</td>
          <td>{{ experiment.seed }}</td>
          <td>{{ experiment.runs }}</td>
          <td>{{ t(`status.${experiment.status}`) }}</td>
          <td>{{ experiment.mean_total_return }}</td>
          <td>{{ experiment.p_negative }}</td>
          <td>{{ experiment.p_ruined }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
