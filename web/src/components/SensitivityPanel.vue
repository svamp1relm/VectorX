<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { getExperiment, runSensitivity } from '../api'
import { usePreferences } from '../preferences'
import type { SensitivityResult } from '../types'
import { useAsyncAnalysis } from './useAsyncAnalysis'

const props = defineProps<{ baseExperimentId: number | null }>()
const emit = defineEmits<{ 'update:loading': [value: boolean] }>()
const { t } = usePreferences()
const gridJson = ref('')
const analysis = useAsyncAnalysis<SensitivityResult>()

watch(() => props.baseExperimentId, analysis.clear)
watch(analysis.loading, (value) => emit('update:loading', value))

const paramKeys = computed(() => [
  ...new Set(
    (analysis.result.value?.points ?? []).flatMap((point) => Object.keys(point.params)),
  ),
])

function formatParam(value: unknown): string {
  return typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value)
}

async function run() {
  await analysis.run(async () => {
    const parsed: unknown = gridJson.value.trim() === '' ? {} : JSON.parse(gridJson.value)
    if (
      typeof parsed !== 'object' ||
      parsed === null ||
      Array.isArray(parsed) ||
      Object.values(parsed).some((values) => !Array.isArray(values) || values.length === 0)
    ) {
      throw new Error(t('robustness.invalidGridError'))
    }
    if (props.baseExperimentId === null) {
      throw new Error(t('robustness.missingBaseError'))
    }
    const detail = await getExperiment(props.baseExperimentId)
    return runSensitivity({
      hypothesis: `Sensitivity: ${detail.name}`,
      base: detail.spec,
      grid: parsed as Record<string, unknown[]>,
    })
  })
}
</script>

<template>
  <section>
    <h3>{{ t('robustness.sensitivityTitle') }}</h3>
    <div class="comparison-controls">
      <label>
        <span>{{ t('batches.grid') }}</span>
        <input v-model="gridJson" type="text" placeholder='{"strategy.fast_period": [8, 10, 12]}' data-testid="sensitivity-grid" />
      </label>
      <button type="button" :disabled="analysis.loading.value" data-testid="sensitivity-run" @click="run">
        {{ t('robustness.run') }}
      </button>
    </div>
    <p v-if="analysis.loading.value" role="status">{{ t('state.loading') }}</p>
    <p v-else-if="analysis.error.value" role="alert">{{ analysis.error.value }}</p>
    <template v-else-if="analysis.result.value">
      <p v-if="analysis.result.value.points.length === 0">{{ t('robustness.noSensitivityPoints') }}</p>
      <table v-else>
        <thead>
          <tr>
            <th v-for="key in paramKeys" :key="key">{{ key }}</th>
            <th>{{ t('robustness.expectancy') }}</th>
            <th>{{ t('detail.sharpe') }}</th>
            <th>{{ t('robustness.expectancyNet') }}</th>
            <th>{{ t('detail.sharpeNet') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(point, index) in analysis.result.value.points" :key="index" data-testid="sensitivity-row">
            <td v-for="key in paramKeys" :key="key">{{ formatParam(point.params[key]) }}</td>
            <td>{{ point.expectancy_sample ?? '—' }}</td>
            <td>{{ point.sharpe ?? '—' }}</td>
            <td>{{ point.expectancy_sample_net ?? '—' }}</td>
            <td>{{ point.sharpe_net ?? '—' }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </section>
</template>
