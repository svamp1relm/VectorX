<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { exportUrl, getAnalysis, getEquity, getExperiment, getResults } from '../api'
import type {
  AnalysisResult,
  EquityPoint,
  ExperimentDetail as ExperimentDetailType,
  RunResult,
} from '../types'
import EquityChart from './EquityChart.vue'
import ExpectancyComparison from './ExpectancyComparison.vue'
import HistogramChart from './HistogramChart.vue'
import RunsTable from './RunsTable.vue'
import { usePreferences } from '../preferences'

const props = defineProps<{ id: number }>()
defineEmits<{ back: [] }>()
const { t } = usePreferences()

const detail = ref<ExperimentDetailType | null>(null)
const results = ref<RunResult[]>([])
const equity = ref<EquityPoint[]>([])
const analysis = ref<AnalysisResult | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

const finalCapital = computed(() => {
  const finalEquity = equity.value.at(-1)?.equity
  if (finalEquity !== undefined) return finalEquity
  const initialCapital = detail.value?.spec.portfolio.initial_capital
  const meanTotalReturn = detail.value?.summary.mean_total_return
  if (initialCapital !== undefined && meanTotalReturn !== undefined) {
    return initialCapital * (1 + meanTotalReturn)
  }
  return null
})
const totalTrades = computed(() => results.value.reduce((total, run) => total + run.metrics.trades, 0))

// Historical specs have no fixed shape worth hardcoding fields for (Фаза 16b):
// render `data`/`strategy`/`portfolio` as a flat, generic key-value list instead.
const historicalParamEntries = computed(() => {
  const spec = detail.value?.spec
  if (!spec || spec.type !== 'historical_backtest') return []
  return [
    ...Object.entries(spec.data).map(([key, value]) => [`data.${key}`, value] as const),
    ...Object.entries(spec.strategy).map(([key, value]) => [`strategy.${key}`, value] as const),
    ...Object.entries(spec.portfolio).map(([key, value]) => [`portfolio.${key}`, value] as const),
  ]
})

function parameterLabel(key: string) {
  return t(`param.${key}`)
}

async function load(id: number) {
  loading.value = true
  error.value = null
  const [detailResult, resultsResult, equityResult, analysisResult] = await Promise.allSettled([
    getExperiment(id),
    getResults(id),
    getEquity(id),
    getAnalysis(id),
  ])

  if (detailResult.status === 'rejected') {
    error.value =
      detailResult.reason instanceof Error ? detailResult.reason.message : String(detailResult.reason)
    loading.value = false
    return
  }
  detail.value = detailResult.value
  results.value = resultsResult.status === 'fulfilled' ? resultsResult.value : []
  equity.value = equityResult.status === 'fulfilled' ? equityResult.value : []
  // Unavailable when the experiment wasn't saved with storage.store_trades=true (Фаза 18a/19).
  analysis.value = analysisResult.status === 'fulfilled' ? analysisResult.value : null
  loading.value = false
}


onMounted(() => load(props.id))
watch(() => props.id, load)
</script>

<template>
  <div>
    <button data-testid="back-button" @click="$emit('back')">&larr; {{ t('actions.back') }}</button>
    <p v-if="loading">{{ t('state.loading') }}</p>
    <p v-else-if="error">{{ error }}</p>
    <template v-else-if="detail">
      <h1>{{ detail.name }}</h1>

      <div class="export-actions">
        <a :href="exportUrl(props.id, 'json')" target="_blank" rel="noopener" data-testid="export-json-link">
          {{ t('detail.exportJson') }}
        </a>
        <a
          :href="exportUrl(props.id, 'markdown')"
          target="_blank"
          rel="noopener"
          data-testid="export-markdown-link"
        >
          {{ t('detail.exportMarkdown') }}
        </a>
      </div>

      <section>
        <h2>{{ t('detail.parameters') }}</h2>
        <dl v-if="detail.spec.type === 'monte_carlo'">
          <dt>{{ t('detail.seed') }}</dt>
          <dd>{{ detail.seed }}</dd>
          <dt>{{ t('detail.pWin') }}</dt>
          <dd>{{ detail.spec.model.p_win }}</dd>
          <dt>{{ t('detail.winR') }}</dt>
          <dd>{{ detail.spec.model.win_r }}</dd>
          <dt>{{ t('detail.lossR') }}</dt>
          <dd>{{ detail.spec.model.loss_r }}</dd>
          <dt>{{ t('detail.nTrades') }}</dt>
          <dd>{{ detail.spec.model.n_trades }}</dd>
          <dt>{{ t('detail.riskUnitFraction') }}</dt>
          <dd>{{ detail.spec.model.risk_unit_fraction }}</dd>
          <dt>{{ t('detail.initialCapital') }}</dt>
          <dd>{{ detail.spec.portfolio.initial_capital }}</dd>
          <dt>{{ t('detail.riskPerTrade') }}</dt>
          <dd>{{ detail.spec.portfolio.risk_per_trade }}</dd>
        </dl>
        <dl v-else>
          <dt>{{ t('detail.type') }}</dt>
          <dd>{{ t(`type.${detail.spec.type}`) }}</dd>
          <template v-for="[key, value] in historicalParamEntries" :key="key">
            <dt>{{ parameterLabel(key) }}</dt>
            <dd>{{ value }}</dd>
          </template>
        </dl>
      </section>

      <ExpectancyComparison :detail="detail" />

      <section>
        <h2>{{ t('detail.summary') }}</h2>
        <dl>
          <dt>{{ t('detail.runs') }}</dt>
          <dd>{{ detail.summary.runs }}</dd>
          <dt>{{ t('detail.finalCapital') }}</dt>
          <dd>{{ finalCapital }}</dd>
          <dt>{{ t('detail.totalTrades') }}</dt>
          <dd>{{ totalTrades }}</dd>
          <dt>{{ t('detail.meanReturn') }}</dt>
          <dd>{{ detail.summary.mean_total_return }}</dd>
          <dt>{{ t('detail.medianReturn') }}</dt>
          <dd>{{ detail.summary.median_total_return }}</dd>
          <dt>{{ t('detail.stdevReturn') }}</dt>
          <dd>{{ detail.summary.stdev_total_return }}</dd>
          <dt>{{ t('detail.negativeProbability') }}</dt>
          <dd>{{ detail.summary.p_negative }}</dd>
          <dt>{{ t('detail.ruinedProbability') }}</dt>
          <dd>{{ detail.summary.p_ruined }}</dd>
        </dl>
      </section>

      <section v-if="analysis" data-testid="analysis-section">
        <h2>{{ t('detail.analysis') }}</h2>
        <dl>
          <dt>{{ t('detail.expectancyCi') }}</dt>
          <dd>
            {{ analysis.confidence_interval.point_estimate }}
            ({{ analysis.confidence_interval.lower }} &ndash; {{ analysis.confidence_interval.upper }})
          </dd>
          <dt>{{ t('detail.significantVsZero') }}</dt>
          <dd>{{ analysis.significance_vs_zero.significant }}</dd>
          <dt>{{ t('detail.sharpe') }}</dt>
          <dd>{{ analysis.risk_adjusted.sharpe }}</dd>
          <dt>{{ t('detail.sortino') }}</dt>
          <dd>{{ analysis.risk_adjusted.sortino }}</dd>
          <dt>{{ t('detail.calmar') }}</dt>
          <dd>{{ analysis.risk_adjusted.calmar }}</dd>
        </dl>
      </section>

      <section>
        <h2>{{ t('detail.equity') }}</h2>
        <EquityChart :points="equity" />
      </section>

      <section>
        <h2>{{ t('detail.totalReturnDistribution') }}</h2>
        <HistogramChart :bins="detail.summary.total_return_histogram" />
      </section>

      <section>
        <h2>{{ t('detail.rMultipleDistribution') }}</h2>
        <HistogramChart :bins="detail.summary.r_multiple_histogram" />
      </section>

      <section>
        <h2>{{ t('detail.runs') }}</h2>
        <p v-if="detail.spec.type === 'historical_backtest'" data-testid="historical-run-note">
          {{ t('detail.historicalRunNote') }}
        </p>
        <RunsTable :results="results" />
      </section>
    </template>
  </div>
</template>
