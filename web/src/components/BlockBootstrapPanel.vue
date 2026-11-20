<script setup lang="ts">
import { ref, watch } from 'vue'
import { getBlockBootstrap } from '../api'
import { usePreferences } from '../preferences'
import type { BlockBootstrapResult } from '../types'
import { useAsyncAnalysis } from './useAsyncAnalysis'

const props = defineProps<{ baseExperimentId: number | null }>()
const emit = defineEmits<{ 'update:loading': [value: boolean] }>()
const { t } = usePreferences()
const blockSize = ref(20)
const seed = ref(0)
const confidence = ref(0.95)
const resamples = ref(2000)
const costBasis = ref<'gross_r' | 'net_r'>('gross_r')
const analysis = useAsyncAnalysis<BlockBootstrapResult>()

watch(() => props.baseExperimentId, analysis.clear)
watch(analysis.loading, (value) => emit('update:loading', value))

async function run() {
  await analysis.run(async () => {
    if (props.baseExperimentId === null) {
      throw new Error(t('robustness.missingBaseError'))
    }
    if (
      blockSize.value <= 0 ||
      seed.value < 0 ||
      confidence.value <= 0 ||
      confidence.value >= 1 ||
      resamples.value <= 0 ||
      resamples.value > 20000
    ) {
      throw new Error(t('robustness.invalidBootstrapFieldsError'))
    }
    return getBlockBootstrap(props.baseExperimentId, {
      blockSize: blockSize.value,
      seed: seed.value,
      confidence: confidence.value,
      nResamples: resamples.value,
      costBasis: costBasis.value,
    })
  })
}
</script>

<template>
  <section>
    <h3>{{ t('robustness.blockBootstrapTitle') }}</h3>
    <p>{{ t('robustness.rawTradesRequired') }}</p>
    <div class="comparison-controls">
      <label><span>{{ t('robustness.blockSize') }}</span><input v-model.number="blockSize" type="number" min="1" data-testid="block-size" /></label>
      <label><span>{{ t('detail.seed') }}</span><input v-model.number="seed" type="number" min="0" data-testid="block-seed" /></label>
      <label><span>{{ t('robustness.confidence') }}</span><input v-model.number="confidence" type="number" min="0.000001" max="0.999999" step="0.01" data-testid="block-confidence" /></label>
      <label><span>{{ t('robustness.resamples') }}</span><input v-model.number="resamples" type="number" min="1" max="20000" data-testid="block-resamples" /></label>
      <label><span>{{ t('robustness.costBasis') }}</span><select v-model="costBasis" data-testid="block-cost-basis"><option value="gross_r">gross_r</option><option value="net_r">net_r</option></select></label>
      <button type="button" :disabled="analysis.loading.value" data-testid="block-bootstrap-run" @click="run">{{ t('robustness.run') }}</button>
    </div>
    <p v-if="analysis.loading.value" role="status">{{ t('state.loading') }}</p>
    <p v-else-if="analysis.error.value" role="alert">{{ analysis.error.value }}</p>
    <dl v-else-if="analysis.result.value" data-testid="block-bootstrap-result">
      <dt>{{ t('robustness.costBasis') }}</dt><dd>{{ analysis.result.value.cost_basis ?? 'gross_r' }}</dd>
      <dt>{{ t('robustness.pointEstimate') }}</dt><dd>{{ analysis.result.value.confidence_interval.point_estimate }}</dd>
      <dt>{{ t('robustness.lowerBound') }}</dt><dd>{{ analysis.result.value.confidence_interval.lower }}</dd>
      <dt>{{ t('robustness.upperBound') }}</dt><dd>{{ analysis.result.value.confidence_interval.upper }}</dd>
    </dl>
  </section>
</template>
