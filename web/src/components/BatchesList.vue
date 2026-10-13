<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { createBatch, getExperiment, listBatches } from '../api'
import { usePreferences } from '../preferences'
import type { BatchSummary } from '../types'

const emit = defineEmits<{ select: [id: number] }>()
const { t } = usePreferences()

const batches = ref<BatchSummary[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const baseExperimentId = ref<number | null>(null)
const hypothesis = ref('')
const notes = ref('')
const gridJson = ref('')
const creating = ref(false)
const createError = ref<string | null>(null)

async function load() {
  loading.value = true
  try {
    batches.value = await listBatches()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function create() {
  createError.value = null
  if (baseExperimentId.value === null || !hypothesis.value) {
    createError.value = t('batches.missingFieldsError')
    return
  }

  let grid: Record<string, unknown[]>
  try {
    grid = gridJson.value.trim() === '' ? {} : JSON.parse(gridJson.value)
  } catch {
    createError.value = t('batches.invalidGridError')
    return
  }

  creating.value = true
  try {
    const base = await getExperiment(baseExperimentId.value)
    await createBatch({
      hypothesis: hypothesis.value,
      notes: notes.value || null,
      base: base.spec,
      grid,
    })
    hypothesis.value = ''
    notes.value = ''
    gridJson.value = ''
    await load()
  } catch (err) {
    createError.value = err instanceof Error ? err.message : String(err)
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div>
    <h2>{{ t('batches.title') }}</h2>

    <section>
      <h3>{{ t('batches.createTitle') }}</h3>
      <div class="comparison-controls">
        <label>
          <span>{{ t('oos.baseExperimentId') }}</span>
          <input v-model.number="baseExperimentId" type="number" data-testid="batch-base-id" />
        </label>
        <label>
          <span>{{ t('batches.hypothesis') }}</span>
          <input v-model="hypothesis" type="text" data-testid="batch-hypothesis" />
        </label>
        <label>
          <span>{{ t('batches.notes') }}</span>
          <input v-model="notes" type="text" data-testid="batch-notes" />
        </label>
        <label>
          <span>{{ t('batches.grid') }}</span>
          <input
            v-model="gridJson"
            type="text"
            placeholder='{"strategy.fast_period": [8, 10, 12]}'
            data-testid="batch-grid"
          />
        </label>
        <button type="button" :disabled="creating" data-testid="batch-create-button" @click="create">
          {{ t('batches.create') }}
        </button>
      </div>
      <p v-if="createError">{{ createError }}</p>
    </section>

    <p v-if="loading">{{ t('state.loading') }}</p>
    <p v-else-if="error">{{ error }}</p>
    <p v-else-if="batches.length === 0">{{ t('batches.empty') }}</p>
    <table v-else>
      <thead>
        <tr>
          <th>{{ t('batches.hypothesis') }}</th>
          <th>{{ t('batches.notes') }}</th>
          <th>{{ t('batches.experimentCount') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="batch in batches"
          :key="batch.id"
          :data-testid="`batch-row-${batch.id}`"
          @click="emit('select', batch.id)"
        >
          <td>{{ batch.hypothesis }}</td>
          <td>{{ batch.notes }}</td>
          <td>{{ batch.experiment_count }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
