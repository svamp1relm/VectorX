<script setup lang="ts">
import { computed, ref } from 'vue'
import { usePreferences } from '../preferences'
import SensitivityPanel from './SensitivityPanel.vue'
import WalkForwardPanel from './WalkForwardPanel.vue'
import BlockBootstrapPanel from './BlockBootstrapPanel.vue'

const { t } = usePreferences()
const baseExperimentId = ref<number | null>(null)
const sensitivityLoading = ref(false)
const walkForwardLoading = ref(false)
const blockBootstrapLoading = ref(false)
const analysisRunning = computed(
  () => sensitivityLoading.value || walkForwardLoading.value || blockBootstrapLoading.value,
)
</script>

<template>
  <div>
    <h2>{{ t('robustness.title') }}</h2>
    <p>{{ t('robustness.description') }}</p>

    <div class="comparison-controls">
      <label>
        <span>{{ t('oos.baseExperimentId') }}</span>
        <input v-model.number="baseExperimentId" type="number" :disabled="analysisRunning" data-testid="robustness-base-id" />
      </label>
    </div>

    <SensitivityPanel :base-experiment-id="baseExperimentId" @update:loading="sensitivityLoading = $event" />
    <WalkForwardPanel :base-experiment-id="baseExperimentId" @update:loading="walkForwardLoading = $event" />
    <BlockBootstrapPanel :base-experiment-id="baseExperimentId" @update:loading="blockBootstrapLoading = $event" />
  </div>
</template>
