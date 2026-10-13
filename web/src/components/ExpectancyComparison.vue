<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { compareExpectancy, listExperiments } from '../api'
import { usePreferences } from '../preferences'
import type {
  ExperimentDetail,
  ExperimentSummaryItem,
  ExpectancyComparisonResult,
  ExpectancyEstimate,
} from '../types'

const props = defineProps<{ detail: ExperimentDetail }>()
const { t } = usePreferences()

const experiments = ref<ExperimentSummaryItem[]>([])
const selectedId = ref<number | null>(null)
const referenceRiskFraction = ref(0.01)
const result = ref<ExpectancyComparisonResult | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const counterpartType = computed(() =>
  props.detail.spec.type === 'monte_carlo' ? 'historical_backtest' : 'monte_carlo',
)
const counterparts = computed(() =>
  experiments.value.filter((experiment) => experiment.spec_type === counterpartType.value),
)
watch(
  counterparts,
  (values) => {
    if (!values.some((experiment) => experiment.id === selectedId.value)) {
      selectedId.value = values[0]?.id ?? null
    }
  },
  { immediate: true },
)
const estimateRows = computed(() => {
  if (!result.value) return []
  return [
    ['theoretical', result.value.estimates.theoretical],
    ['sample', result.value.estimates.sample],
    ['historical', result.value.estimates.historical],
  ] as const
})

function sampleLabel(estimate: ExpectancyEstimate | null) {
  if (!estimate) return '—'
  const actual = estimate.sample_size ?? '—'
  if (estimate.planned_sample_size === null) return String(actual)
  return `${actual} / ${estimate.planned_sample_size}`
}

async function compare() {
  if (selectedId.value === null) return
  loading.value = true
  error.value = null
  try {
    const monteCarloExperimentId =
      props.detail.spec.type === 'monte_carlo' ? props.detail.id : selectedId.value
    const historicalExperimentId =
      props.detail.spec.type === 'historical_backtest' ? props.detail.id : selectedId.value
    result.value = await compareExpectancy({
      monteCarloExperimentId,
      historicalExperimentId,
      referenceRiskFraction: referenceRiskFraction.value,
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  experiments.value = await listExperiments()
})
</script>

<template>
  <section data-testid="expectancy-comparison">
    <h2>{{ t('comparison.title') }}</h2>
    <p>{{ t('comparison.description') }}</p>

    <div class="comparison-controls">
      <label>
        <span>{{ t('comparison.counterpart') }}</span>
        <select v-model.number="selectedId" data-testid="comparison-counterpart">
          <option v-for="experiment in counterparts" :key="experiment.id" :value="experiment.id">
            {{ experiment.name }}
          </option>
        </select>
      </label>
      <label>
        <span>{{ t('comparison.referenceRisk') }}</span>
        <input
          v-model.number="referenceRiskFraction"
          type="number"
          min="0.000001"
          max="1"
          step="0.001"
          data-testid="reference-risk-fraction"
        />
      </label>
      <button
        type="button"
        :disabled="selectedId === null || loading"
        data-testid="run-comparison"
        @click="compare"
      >
        {{ loading ? t('state.loading') : t('comparison.compare') }}
      </button>
    </div>

    <p v-if="counterparts.length === 0">{{ t('comparison.noCounterpart') }}</p>
    <p v-else-if="error" class="comparison-warning">{{ error }}</p>

    <template v-if="result">
      <table data-testid="comparison-values">
        <thead>
          <tr>
            <th>{{ t('comparison.estimate') }}</th>
            <th>{{ t('comparison.sourceValue') }}</th>
            <th>{{ t('comparison.referenceValue') }}</th>
            <th>{{ t('comparison.sampleSize') }}</th>
            <th>{{ t('comparison.riskUnitFraction') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="[key, estimate] in estimateRows" :key="key">
            <td>{{ t(`comparison.${key}`) }}</td>
            <td>{{ estimate?.value ?? '—' }}</td>
            <td>{{ estimate?.canonical_value ?? '—' }}</td>
            <td>{{ sampleLabel(estimate) }}</td>
            <td>{{ estimate?.risk_definition.risk_unit_fraction ?? '—' }}</td>
          </tr>
        </tbody>
      </table>

      <table data-testid="comparison-deltas">
        <thead>
          <tr>
            <th>{{ t('comparison.delta') }}</th>
            <th>{{ t('comparison.referenceValue') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>{{ t('comparison.deltaTheoreticalSample') }}</td>
            <td>{{ result.deltas.delta_theoretical_sample ?? '—' }}</td>
          </tr>
          <tr>
            <td>{{ t('comparison.deltaTheoreticalHistorical') }}</td>
            <td>{{ result.deltas.delta_theoretical_historical ?? '—' }}</td>
          </tr>
          <tr>
            <td>{{ t('comparison.deltaSampleHistorical') }}</td>
            <td>{{ result.deltas.delta_sample_historical ?? '—' }}</td>
          </tr>
        </tbody>
      </table>

      <p v-if="result.warnings.length" class="comparison-warning" data-testid="comparison-warning">
        {{
          result.risk_compatibility.compatible
            ? t('comparison.convertedWarning')
            : t('comparison.incompatibleWarning')
        }}
      </p>
    </template>
  </section>
</template>
