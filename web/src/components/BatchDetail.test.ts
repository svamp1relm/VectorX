import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import type { BatchDetail as BatchDetailType } from '../types'

const getBatch = vi.fn()
vi.mock('../api', () => ({ getBatch: (...args: unknown[]) => getBatch(...args) }))

const { default: BatchDetail } = await import('./BatchDetail.vue')

const detail: BatchDetailType = {
  id: 1,
  hypothesis: 'fast period matters',
  notes: 'first sweep',
  created_at: '2026-10-02T00:00:00Z',
  experiments: [
    {
      id: 10,
      name: 'sweep_test_0',
      spec_type: 'monte_carlo',
      seed: 42,
      runs: 5,
      status: 'completed',
      created_at: '2026-10-02T00:00:00Z',
      experiment_version: 1,
      code_version: 'unknown',
      mean_total_return: 0.2,
      median_total_return: 0.2,
      stdev_total_return: 0.05,
      p_negative: 0.0,
      p_ruined: 0.0,
    },
  ],
}

describe('BatchDetail', () => {
  it('fetches the batch on mount and renders its hypothesis and experiments', async () => {
    getBatch.mockResolvedValueOnce(detail)

    const wrapper = mount(BatchDetail, { props: { id: 1 } })
    await flushPromises()

    expect(getBatch).toHaveBeenCalledWith(1)
    expect(wrapper.text()).toContain('fast period matters')
    expect(wrapper.text()).toContain('sweep_test_0')
  })

  it('emits selectExperiment with the experiment id when a row is clicked', async () => {
    getBatch.mockResolvedValueOnce(detail)

    const wrapper = mount(BatchDetail, { props: { id: 1 } })
    await flushPromises()
    await wrapper.find('[data-testid="batch-experiment-row-10"]').trigger('click')

    expect(wrapper.emitted('selectExperiment')).toEqual([[10]])
  })

  it('emits back when the back button is clicked', async () => {
    getBatch.mockResolvedValueOnce(detail)

    const wrapper = mount(BatchDetail, { props: { id: 1 } })
    await flushPromises()
    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('back')).toBeTruthy()
  })
})
