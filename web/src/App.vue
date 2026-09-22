<script setup lang="ts">
import { ref } from 'vue'
import ExperimentDetail from './components/ExperimentDetail.vue'
import ExperimentsList from './components/ExperimentsList.vue'

const selectedId = ref<number | null>(null)
</script>

<template>
  <main>
    <ExperimentsList v-if="selectedId === null" @select="(id) => (selectedId = id)" />
    <ExperimentDetail v-else :id="selectedId" @back="selectedId = null" />
  </main>
</template>
