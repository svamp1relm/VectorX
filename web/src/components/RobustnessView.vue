<script setup lang="ts">
import { computed, ref } from 'vue'
import { getBlockBootstrap, getExperiment, runSensitivity, runWalkForward } from '../api'
import { usePreferences } from '../preferences'
import type {
  BlockBootstrapResult,
  ExpectancyEstimateLite,
  SensitivityResult,
  WalkForwardResult,
} from '../types'

const { t } = usePreferences()

const baseExperimentId = ref<number | null>(null)

const sensitivityGrid = ref('')
const sensitivityLoading = ref(false)
const sensitivityError = ref<string | null>(null)
const sensitivityResult = ref<SensitivityResult | null>(null)

const walkStart = ref('')
const walkEnd = ref('')
const trainWindowDays = ref(365)
const testWindowDays = ref(90)
const stepDays = ref(90)
const walkForwardLoading = ref(false)
const walkForwardError = ref<string | null>(null)
const walkForwardResult = ref<WalkForwardResult | null>(null)

const blockSize = ref(20)
const blockSeed = ref(0)
const blockConfidence = ref(0.95)
const blockResamples = ref(2000)
const blockBootstrapLoading = ref(false)
const blockBootstrapError = ref<string | null>(null)
const blockBootstrapResult = ref<BlockBootstrapResult | null>(null)

const sensitivityParamKeys = computed(() => [
  ...new Set(
    (sensitivityResult.value?.points ?? []).flatMap((point) => Object.keys(point.params)),
  ),
])

function requireBaseExperimentId(): number {
  if (baseExperimentId.value === null) {
    throw new Error(t('robustness.missingBaseError'))
  }
  return baseExperimentId.value
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

function formatParam(value: unknown): string {
  return typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value)
}

function estimateValue(estimate: ExpectancyEstimateLite): number {
  return estimate.canonical_value ?? estimate.value
}

async function runSensitivityAnalysis() {
  sensitivityError.value = null
  sensitivityResult.value = null
  let grid: Record<string, unknown[]>
  try {
    const parsed: unknown = sensitivityGrid.value.trim() === '' ? {} : JSON.parse(sensitivityGrid.value)
    if (
      typeof parsed !== 'object' ||
      parsed === null ||
      Array.isArray(parsed) ||
      Object.values(parsed).some((values) => !Array.isArray(values))
    ) {
      throw new Error(t('robustness.invalidGridError'))
    }
    grid = parsed as Record<string, unknown[]>
    const id = requireBaseExperimentId()
    sensitivityLoading.value = true
    const detail = await getExperiment(id)
    sensitivityResult.value = await runSensitivity({
      hypothesis: `Sensitivity: ${detail.name}`,
      base: detail.spec,
      grid,
    })
  } catch (error) {
    sensitivityError.value = errorMessage(error)
  } finally {
    sensitivityLoading.value = false
  }
}

async function runWalkForwardAnalysis() {
  walkForwardError.value = null
  walkForwardResult.value = null
  try {
    const id = requireBaseExperimentId()
    if (!walkStart.value || !walkEnd.value) {
      throw new Error(t('robustness.missingWalkForwardFieldsError'))
    }
    walkForwardLoading.value = true
    const detail = await getExperiment(id)
    if (detail.spec.type !== 'historical_backtest') {
      throw new Error(t('robustness.notHistoricalError'))
    }
    walkForwardResult.value = await runWalkForward({
      base: detail.spec,
      start: walkStart.value,
      end: walkEnd.value,
      train_window_days: trainWindowDays.value,
      test_window_days: testWindowDays.value,
      step_days: stepDays.value,
      reference_risk_fraction: 0.01,
    })
  } catch (error) {
    walkForwardError.value = errorMessage(error)
  } finally {
    walkForwardLoading.value = false
  }
}

async function runBlockBootstrap() {
  blockBootstrapError.value = null
  blockBootstrapResult.value = null
  try {
    const id = requireBaseExperimentId()
    blockBootstrapLoading.value = true
    blockBootstrapResult.value = await getBlockBootstrap(id, {
      blockSize: blockSize.value,
      seed: blockSeed.value,
      confidence: blockConfidence.value,
      nResamples: blockResamples.value,
    })
  } catch (error) {
    blockBootstrapError.value = errorMessage(error)
  } finally {
    blockBootstrapLoading.value = false
  }
}
</script>

<template>
  <div>
    <h2>{{ t('robustness.title') }}</h2>
    <p>{{ t('robustness.description') }}</p>

    <div class="comparison-controls">
      <label>
        <span>{{ t('oos.baseExperimentId') }}</span>
        <input v-model.number="baseExperimentId" type="number" data-testid="robustness-base-id" />
      </label>
    </div>

    <section>
      <h3>{{ t('robustness.sensitivityTitle') }}</h3>
      <div class="comparison-controls">
        <label>
          <span>{{ t('batches.grid') }}</span>
          <input
            v-model="sensitivityGrid"
            type="text"
            placeholder='{"strategy.fast_period": [8, 10, 12]}'
            data-testid="sensitivity-grid"
          />
        </label>
        <button
          type="button"
          :disabled="sensitivityLoading"
          data-testid="sensitivity-run"
          @click="runSensitivityAnalysis"
        >
          {{ t('robustness.run') }}
        </button>
      </div>
      <p v-if="sensitivityLoading">{{ t('state.loading') }}</p>
      <p v-else-if="sensitivityError" role="alert">{{ sensitivityError }}</p>
      <table v-else-if="sensitivityResult">
        <thead>
          <tr>
            <th v-for="key in sensitivityParamKeys" :key="key">{{ key }}</th>
            <th>{{ t('robustness.expectancy') }}</th>
            <th>{{ t('detail.sharpe') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(point, index) in sensitivityResult.points"
            :key="index"
            data-testid="sensitivity-row"
          >
            <td v-for="key in sensitivityParamKeys" :key="key">{{ formatParam(point.params[key]) }}</td>
            <td>{{ point.expectancy_sample }}</td>
            <td>{{ point.sharpe }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section>
      <h3>{{ t('robustness.walkForwardTitle') }}</h3>
      <div class="comparison-controls">
        <label>
          <span>{{ t('robustness.rangeStart') }}</span>
          <input v-model="walkStart" type="text" placeholder="2024-01-01T00:00:00+00:00" data-testid="walk-forward-start" />
        </label>
        <label>
          <span>{{ t('robustness.rangeEnd') }}</span>
          <input v-model="walkEnd" type="text" placeholder="2026-01-01T00:00:00+00:00" data-testid="walk-forward-end" />
        </label>
        <label>
          <span>{{ t('robustness.trainDays') }}</span>
          <input v-model.number="trainWindowDays" type="number" min="0" data-testid="walk-forward-train-days" />
        </label>
        <label>
          <span>{{ t('robustness.testDays') }}</span>
          <input v-model.number="testWindowDays" type="number" min="0" data-testid="walk-forward-test-days" />
        </label>
        <label>
          <span>{{ t('robustness.stepDays') }}</span>
          <input v-model.number="stepDays" type="number" min="0" data-testid="walk-forward-step-days" />
        </label>
        <button
          type="button"
          :disabled="walkForwardLoading"
          data-testid="walk-forward-run"
          @click="runWalkForwardAnalysis"
        >
          {{ t('robustness.run') }}
        </button>
      </div>
      <p v-if="walkForwardLoading">{{ t('state.loading') }}</p>
      <p v-else-if="walkForwardError" role="alert">{{ walkForwardError }}</p>
      <table v-else-if="walkForwardResult">
        <thead>
          <tr>
            <th>{{ t('robustness.window') }}</th>
            <th>{{ t('oos.trainStart') }}</th>
            <th>{{ t('oos.testEnd') }}</th>
            <th>{{ t('robustness.trainExpectancy') }}</th>
            <th>{{ t('robustness.testExpectancy') }}</th>
            <th>{{ t('oos.deltaTrainTest') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(item, index) in walkForwardResult.windows"
            :key="index"
            data-testid="walk-forward-row"
          >
            <td>{{ index + 1 }}</td>
            <td>{{ item.window.train_start }}</td>
            <td>{{ item.window.test_end }}</td>
            <td>{{ estimateValue(item.result.comparison.train) }}</td>
            <td>{{ estimateValue(item.result.comparison.test) }}</td>
            <td>{{ item.result.comparison.delta_train_test }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section>
      <h3>{{ t('robustness.blockBootstrapTitle') }}</h3>
      <p>{{ t('robustness.rawTradesRequired') }}</p>
      <div class="comparison-controls">
        <label>
          <span>{{ t('robustness.blockSize') }}</span>
          <input v-model.number="blockSize" type="number" min="1" data-testid="block-size" />
        </label>
        <label>
          <span>{{ t('detail.seed') }}</span>
          <input v-model.number="blockSeed" type="number" data-testid="block-seed" />
        </label>
        <label>
          <span>{{ t('robustness.confidence') }}</span>
          <input v-model.number="blockConfidence" type="number" min="0" max="1" step="0.01" data-testid="block-confidence" />
        </label>
        <label>
          <span>{{ t('robustness.resamples') }}</span>
          <input v-model.number="blockResamples" type="number" min="1" max="20000" data-testid="block-resamples" />
        </label>
        <button
          type="button"
          :disabled="blockBootstrapLoading"
          data-testid="block-bootstrap-run"
          @click="runBlockBootstrap"
        >
          {{ t('robustness.run') }}
        </button>
      </div>
      <p v-if="blockBootstrapLoading">{{ t('state.loading') }}</p>
      <p v-else-if="blockBootstrapError" role="alert">{{ blockBootstrapError }}</p>
      <dl v-else-if="blockBootstrapResult" data-testid="block-bootstrap-result">
        <dt>{{ t('robustness.pointEstimate') }}</dt>
        <dd>{{ blockBootstrapResult.confidence_interval.point_estimate }}</dd>
        <dt>{{ t('robustness.lowerBound') }}</dt>
        <dd>{{ blockBootstrapResult.confidence_interval.lower }}</dd>
        <dt>{{ t('robustness.upperBound') }}</dt>
        <dd>{{ blockBootstrapResult.confidence_interval.upper }}</dd>
      </dl>
    </section>
  </div>
</template>
