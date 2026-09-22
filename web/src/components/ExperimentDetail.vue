<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { getEquity, getExperiment, getResults } from '../api'
import type {
  EquityPoint,
  ExperimentDetail as ExperimentDetailType,
  RunResult,
} from '../types'
import EquityChart from './EquityChart.vue'
import HistogramChart from './HistogramChart.vue'
import RunsTable from './RunsTable.vue'

const props = defineProps<{ id: number }>()
defineEmits<{ back: [] }>()

const detail = ref<ExperimentDetailType | null>(null)
const results = ref<RunResult[]>([])
const equity = ref<EquityPoint[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

async function load(id: number) {
  loading.value = true
  error.value = null
  try {
    const [detailData, resultsData, equityData] = await Promise.all([
      getExperiment(id),
      getResults(id),
      getEquity(id),
    ])
    detail.value = detailData
    results.value = resultsData
    equity.value = equityData
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
    <button data-testid="back-button" @click="$emit('back')">&larr; Back</button>
    <p v-if="loading">Loading…</p>
    <p v-else-if="error">{{ error }}</p>
    <template v-else-if="detail">
      <h1>{{ detail.name }}</h1>

      <section>
        <h2>Parameters</h2>
        <dl>
          <dt>Seed</dt>
          <dd>{{ detail.seed }}</dd>
          <dt>p_win</dt>
          <dd>{{ detail.spec.model.p_win }}</dd>
          <dt>win_r</dt>
          <dd>{{ detail.spec.model.win_r }}</dd>
          <dt>loss_r</dt>
          <dd>{{ detail.spec.model.loss_r }}</dd>
          <dt>n_trades</dt>
          <dd>{{ detail.spec.model.n_trades }}</dd>
          <dt>initial_capital</dt>
          <dd>{{ detail.spec.portfolio.initial_capital }}</dd>
          <dt>risk_per_trade</dt>
          <dd>{{ detail.spec.portfolio.risk_per_trade }}</dd>
        </dl>
      </section>

      <section>
        <h2>Summary</h2>
        <dl>
          <dt>Runs</dt>
          <dd>{{ detail.summary.runs }}</dd>
          <dt>Mean total return</dt>
          <dd>{{ detail.summary.mean_total_return }}</dd>
          <dt>Median total return</dt>
          <dd>{{ detail.summary.median_total_return }}</dd>
          <dt>Stdev total return</dt>
          <dd>{{ detail.summary.stdev_total_return }}</dd>
          <dt>P(negative)</dt>
          <dd>{{ detail.summary.p_negative }}</dd>
          <dt>P(ruined)</dt>
          <dd>{{ detail.summary.p_ruined }}</dd>
        </dl>
      </section>

      <section>
        <h2>Equity</h2>
        <EquityChart :points="equity" />
      </section>

      <section>
        <h2>Total return distribution</h2>
        <HistogramChart :bins="detail.summary.total_return_histogram" />
      </section>

      <section>
        <h2>R-multiple distribution</h2>
        <HistogramChart :bins="detail.summary.r_multiple_histogram" />
      </section>

      <section>
        <h2>Runs</h2>
        <RunsTable :results="results" />
      </section>
    </template>
  </div>
</template>
