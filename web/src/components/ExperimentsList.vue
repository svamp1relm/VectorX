<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listExperiments } from '../api'
import type { ExperimentSummaryItem } from '../types'

const emit = defineEmits<{ select: [id: number] }>()

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
    <h1>Experiments</h1>
    <p v-if="loading">Loading…</p>
    <p v-else-if="error">{{ error }}</p>
    <p v-else-if="experiments.length === 0">No experiments yet.</p>
    <table v-else>
      <thead>
        <tr>
          <th>Name</th>
          <th>Seed</th>
          <th>Runs</th>
          <th>Status</th>
          <th>Mean total return</th>
          <th>P(negative)</th>
          <th>P(ruined)</th>
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
          <td>{{ experiment.status }}</td>
          <td>{{ experiment.mean_total_return }}</td>
          <td>{{ experiment.p_negative }}</td>
          <td>{{ experiment.p_ruined }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
