<script setup lang="ts">
import { ref } from 'vue'
import BatchDetail from './components/BatchDetail.vue'
import BatchesList from './components/BatchesList.vue'
import ExperimentDetail from './components/ExperimentDetail.vue'
import ExperimentsList from './components/ExperimentsList.vue'
import OutOfSampleView from './components/OutOfSampleView.vue'
import { usePreferences } from './preferences'

type View = 'experiments' | 'batches' | 'out-of-sample'

const view = ref<View>('experiments')
const selectedId = ref<number | null>(null)
const selectedBatchId = ref<number | null>(null)
const { locale, theme, setLocale, setTheme, t } = usePreferences()

function showExperiments() {
  view.value = 'experiments'
  selectedId.value = null
  selectedBatchId.value = null
}

function showBatches() {
  view.value = 'batches'
  selectedId.value = null
  selectedBatchId.value = null
}

function showOutOfSample() {
  view.value = 'out-of-sample'
  selectedId.value = null
  selectedBatchId.value = null
}
</script>

<template>
  <main>
    <header class="app-header">
      <div>
        <h1>{{ t('app.title') }}</h1>
        <p>{{ t('app.subtitle') }}</p>
      </div>
      <nav class="preference-control" data-testid="view-switch">
        <div class="segmented-control">
          <button type="button" :class="{ active: view === 'experiments' }" @click="showExperiments">
            {{ t('list.title') }}
          </button>
          <button type="button" :class="{ active: view === 'batches' }" @click="showBatches">
            {{ t('batches.title') }}
          </button>
          <button type="button" :class="{ active: view === 'out-of-sample' }" @click="showOutOfSample">
            {{ t('oos.title') }}
          </button>
        </div>
      </nav>
      <div class="preferences">
        <div class="preference-control" data-testid="language-switch">
          <span>{{ t('controls.language') }}</span>
          <div class="segmented-control">
            <button
              type="button"
              :aria-pressed="locale === 'en'"
              :class="{ active: locale === 'en' }"
              @click="setLocale('en')"
            >
              {{ t('controls.english') }}
            </button>
            <button
              type="button"
              :aria-pressed="locale === 'ru'"
              :class="{ active: locale === 'ru' }"
              @click="setLocale('ru')"
            >
              {{ t('controls.russian') }}
            </button>
          </div>
        </div>
        <div class="preference-control" data-testid="theme-switch">
          <span>{{ t('controls.theme') }}</span>
          <div class="segmented-control">
            <button
              type="button"
              :aria-pressed="theme === 'light'"
              :class="{ active: theme === 'light' }"
              @click="setTheme('light')"
            >
              {{ t('controls.light') }}
            </button>
            <button
              type="button"
              :aria-pressed="theme === 'dark'"
              :class="{ active: theme === 'dark' }"
              @click="setTheme('dark')"
            >
              {{ t('controls.dark') }}
            </button>
          </div>
        </div>
      </div>
    </header>
    <template v-if="view === 'experiments'">
      <ExperimentsList v-if="selectedId === null" @select="(id) => (selectedId = id)" />
      <ExperimentDetail v-else :id="selectedId" @back="selectedId = null" />
    </template>
    <template v-else-if="view === 'batches'">
      <BatchesList v-if="selectedBatchId === null" @select="(id) => (selectedBatchId = id)" />
      <BatchDetail
        v-else
        :id="selectedBatchId"
        @back="selectedBatchId = null"
        @select-experiment="
          (id) => {
            view = 'experiments'
            selectedBatchId = null
            selectedId = id
          }
        "
      />
    </template>
    <OutOfSampleView v-else />
  </main>
</template>

