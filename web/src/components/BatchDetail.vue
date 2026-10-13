<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { getBatch } from '../api'
import { usePreferences } from '../preferences'
import type { BatchDetail as BatchDetailType } from '../types'

const props = defineProps<{ id: number }>()
const emit = defineEmits<{ back: []; selectExperiment: [id: number] }>()
const { t } = usePreferences()

const batch = ref<BatchDetailType | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

async function load(id: number) {
  loading.value = true
  error.value = null
  try {
    batch.value = await getBatch(id)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

onMounted(() => load(props.id))
watch(() => props.id, load)
</script>

<template>
  <div>
    <button type="button" @click="emit('back')">{{ t('actions.back') }}</button>
    <p v-if="loading">{{ t('state.loading') }}</p>
    <p v-else-if="error">{{ error }}</p>
    <template v-else-if="batch">
      <h2>{{ batch.hypothesis }}</h2>
      <p v-if="batch.notes">{{ batch.notes }}</p>
      <table>
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
            v-for="experiment in batch.experiments"
            :key="experiment.id"
            :data-testid="`batch-experiment-row-${experiment.id}`"
            @click="emit('selectExperiment', experiment.id)"
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
    </template>
  </div>
</template>
