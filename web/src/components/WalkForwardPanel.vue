<script setup lang="ts">
import { ref, watch } from 'vue'
import { getExperiment, runWalkForward } from '../api'
import { usePreferences } from '../preferences'
import type { ExpectancyEstimateLite, WalkForwardResult } from '../types'
import { useAsyncAnalysis } from './useAsyncAnalysis'

const props = defineProps<{ baseExperimentId: number | null }>()
const emit = defineEmits<{ 'update:loading': [value: boolean] }>()
const { t } = usePreferences()
const start = ref('')
const end = ref('')
const trainDays = ref(365)
const testDays = ref(90)
const stepDays = ref(90)
const analysis = useAsyncAnalysis<WalkForwardResult>()

watch(() => props.baseExperimentId, analysis.clear)
watch(analysis.loading, (value) => emit('update:loading', value))

function estimateValue(estimate: ExpectancyEstimateLite | null): number | string {
  return estimate === null ? '—' : estimate.canonical_value ?? estimate.value
}

async function run() {
  await analysis.run(async () => {
    if (
      props.baseExperimentId === null ||
      !start.value ||
      !end.value ||
      trainDays.value <= 0 ||
      testDays.value <= 0 ||
      stepDays.value <= 0
    ) {
      throw new Error(t('robustness.missingWalkForwardFieldsError'))
    }
    const detail = await getExperiment(props.baseExperimentId)
    if (detail.spec.type !== 'historical_backtest') {
      throw new Error(t('robustness.notHistoricalError'))
    }
    return runWalkForward({
      base: detail.spec,
      start: start.value,
      end: end.value,
      train_window_days: trainDays.value,
      test_window_days: testDays.value,
      step_days: stepDays.value,
      reference_risk_fraction: 0.01,
    })
  })
}
</script>

<template>
  <section>
    <h3>{{ t('robustness.walkForwardTitle') }}</h3>
    <div class="comparison-controls">
      <label><span>{{ t('robustness.rangeStart') }}</span><input v-model="start" type="text" placeholder="2024-01-01T00:00:00+00:00" data-testid="walk-forward-start" /></label>
      <label><span>{{ t('robustness.rangeEnd') }}</span><input v-model="end" type="text" placeholder="2026-01-01T00:00:00+00:00" data-testid="walk-forward-end" /></label>
      <label><span>{{ t('robustness.trainDays') }}</span><input v-model.number="trainDays" type="number" min="0.000001" data-testid="walk-forward-train-days" /></label>
      <label><span>{{ t('robustness.testDays') }}</span><input v-model.number="testDays" type="number" min="0.000001" data-testid="walk-forward-test-days" /></label>
      <label><span>{{ t('robustness.stepDays') }}</span><input v-model.number="stepDays" type="number" min="0.000001" data-testid="walk-forward-step-days" /></label>
      <button type="button" :disabled="analysis.loading.value" data-testid="walk-forward-run" @click="run">{{ t('robustness.run') }}</button>
    </div>
    <p v-if="analysis.loading.value" role="status">{{ t('state.loading') }}</p>
    <p v-else-if="analysis.error.value" role="alert">{{ analysis.error.value }}</p>
    <table v-else-if="analysis.result.value">
      <thead><tr><th>{{ t('robustness.window') }}</th><th>{{ t('oos.trainStart') }}</th><th>{{ t('oos.testEnd') }}</th><th>{{ t('robustness.trainExpectancy') }}</th><th>{{ t('robustness.testExpectancy') }}</th><th>{{ t('oos.deltaTrainTest') }}</th></tr></thead>
      <tbody>
        <tr v-for="(item, index) in analysis.result.value.windows" :key="index" data-testid="walk-forward-row">
          <td>{{ index + 1 }}</td><td>{{ item.window.train_start }}</td><td>{{ item.window.test_end }}</td>
          <td>{{ estimateValue(item.result.comparison.train) }}</td><td>{{ estimateValue(item.result.comparison.test) }}</td>
          <td>{{ item.result.comparison.delta_train_test ?? '—' }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
