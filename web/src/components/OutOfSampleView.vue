<script setup lang="ts">
import { ref } from 'vue'
import { getExperiment, runOutOfSample } from '../api'
import { usePreferences } from '../preferences'
import type { HistoricalBacktestExperimentSpec, OutOfSampleResult } from '../types'

const { t } = usePreferences()

const baseExperimentId = ref<number | null>(null)
const trainStart = ref('')
const trainEnd = ref('')
const testStart = ref('')
const testEnd = ref('')
const result = ref<OutOfSampleResult | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

async function run() {
  if (baseExperimentId.value === null) return
  if (!trainStart.value || !trainEnd.value || !testStart.value || !testEnd.value) {
    error.value = t('oos.missingDatesError')
    return
  }
  loading.value = true
  error.value = null
  result.value = null
  try {
    const detail = await getExperiment(baseExperimentId.value)
    if (detail.spec.type !== 'historical_backtest') {
      throw new Error(t('oos.notHistoricalError'))
    }
    result.value = await runOutOfSample({
      base: detail.spec as HistoricalBacktestExperimentSpec,
      train_start: trainStart.value,
      train_end: trainEnd.value,
      test_start: testStart.value,
      test_end: testEnd.value,
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h2>{{ t('oos.title') }}</h2>
    <div class="comparison-controls">
      <label>
        <span>{{ t('oos.baseExperimentId') }}</span>
        <input v-model.number="baseExperimentId" type="number" data-testid="oos-base-id" />
      </label>
      <label>
        <span>{{ t('oos.trainStart') }}</span>
        <input
          v-model="trainStart"
          type="text"
          placeholder="2024-01-01T00:00:00+00:00"
          data-testid="oos-train-start"
        />
      </label>
      <label>
        <span>{{ t('oos.trainEnd') }}</span>
        <input
          v-model="trainEnd"
          type="text"
          placeholder="2025-01-01T00:00:00+00:00"
          data-testid="oos-train-end"
        />
      </label>
      <label>
        <span>{{ t('oos.testStart') }}</span>
        <input
          v-model="testStart"
          type="text"
          placeholder="2025-01-01T01:00:00+00:00"
          data-testid="oos-test-start"
        />
      </label>
      <label>
        <span>{{ t('oos.testEnd') }}</span>
        <input
          v-model="testEnd"
          type="text"
          placeholder="2026-01-01T00:00:00+00:00"
          data-testid="oos-test-end"
        />
      </label>
      <button type="button" data-testid="oos-run-button" @click="run">{{ t('oos.run') }}</button>
    </div>

    <p v-if="loading">{{ t('state.loading') }}</p>
    <p v-else-if="error">{{ error }}</p>
    <template v-else-if="result">
      <section>
        <h3>{{ t('oos.train') }}</h3>
        <p>{{ result.train.summary.mean_total_return }}</p>
      </section>
      <section>
        <h3>{{ t('oos.test') }}</h3>
        <p>{{ result.test.summary.mean_total_return }}</p>
      </section>
      <section>
        <h3>{{ t('oos.deltaTrainTest') }}</h3>
        <p data-testid="oos-delta">{{ result.comparison.delta_train_test }}</p>
      </section>
    </template>
  </div>
</template>
