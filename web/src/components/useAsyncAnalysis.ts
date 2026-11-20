import { ref } from 'vue'

export function useAsyncAnalysis<T>() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const result = ref<T | null>(null)
  let requestId = 0

  async function run(task: () => Promise<T>) {
    const currentRequest = ++requestId
    loading.value = true
    error.value = null
    result.value = null
    try {
      const nextResult = await task()
      if (currentRequest === requestId) result.value = nextResult
    } catch (reason) {
      if (currentRequest === requestId) {
        error.value = reason instanceof Error ? reason.message : String(reason)
      }
    } finally {
      if (currentRequest === requestId) loading.value = false
    }
  }

  function clear() {
    requestId += 1
    loading.value = false
    error.value = null
    result.value = null
  }

  return { loading, error, result, run, clear }
}
