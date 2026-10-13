import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import type { ExperimentSummaryItem } from '../types'

const listExperiments = vi.fn()
vi.mock('../api', () => ({ listExperiments: (...args: unknown[]) => listExperiments(...args) }))

const { default: ExperimentsList } = await import('./ExperimentsList.vue')

const items: ExperimentSummaryItem[] = [
  {
    id: 1,
    name: 'baseline_expectancy',
    spec_type: 'monte_carlo',
    seed: 42,
    runs: 100,
    status: 'completed',
    created_at: '2026-09-22T00:00:00Z',
    experiment_version: 1,
    code_version: 'unknown',
    mean_total_return: 0.3,
    median_total_return: 0.28,
    stdev_total_return: 0.1,
    p_negative: 0.0,
    p_ruined: 0.0,
  },
]

describe('ExperimentsList', () => {
  it('fetches experiments on mount and renders one row per experiment', async () => {
    listExperiments.mockResolvedValueOnce(items)

    const wrapper = mount(ExperimentsList)
    await flushPromises()

    expect(listExperiments).toHaveBeenCalledOnce()
    expect(wrapper.text()).toContain('baseline_expectancy')
    expect(wrapper.text()).toContain('42')
  })

  it('emits select with the experiment id when a row is clicked', async () => {
    listExperiments.mockResolvedValueOnce(items)

    const wrapper = mount(ExperimentsList)
    await flushPromises()
    await wrapper.find('[data-testid="experiment-row-1"]').trigger('click')

    expect(wrapper.emitted('select')).toEqual([[1]])
  })

  it('shows an empty state with no experiments', async () => {
    listExperiments.mockResolvedValueOnce([])

    const wrapper = mount(ExperimentsList)
    await flushPromises()

    expect(wrapper.text()).toContain('No experiments')
  })
})
