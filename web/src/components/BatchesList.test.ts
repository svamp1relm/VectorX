import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import type { BatchSummary, ExperimentDetail } from '../types'

const listBatches = vi.fn()
const createBatch = vi.fn()
const getExperiment = vi.fn()
vi.mock('../api', () => ({
  listBatches: (...args: unknown[]) => listBatches(...args),
  createBatch: (...args: unknown[]) => createBatch(...args),
  getExperiment: (...args: unknown[]) => getExperiment(...args),
}))

const { default: BatchesList } = await import('./BatchesList.vue')

const items: BatchSummary[] = [
  {
    id: 1,
    hypothesis: 'fast period matters',
    notes: 'first sweep',
    created_at: '2026-10-02T00:00:00Z',
    experiment_count: 3,
  },
]

const baseExperiment: ExperimentDetail = {
  id: 1,
  name: 'btc_1h_ma_crossover',
  seed: 0,
  runs: 1,
  status: 'completed',
  created_at: '2026-10-02T00:00:00Z',
  duration: 0.01,
  experiment_version: 1,
  code_version: 'unknown',
  spec: {
    type: 'historical_backtest',
    name: 'btc_1h_ma_crossover',
    seed: 0,
    runs: 1,
    data: { source: 'csv', path: 'data.csv', symbol: 'BTCUSDT', timeframe: '1h' },
    strategy: { type: 'moving_average_crossover', fast_period: 10, slow_period: 30, stop_loss_pct: 0.01 },
    portfolio: { initial_capital: 10_000, risk_per_trade: 0.01, commission: 0, slippage: 0 },
    storage: { store_trades: false },
  },
  summary: {
    runs: 1,
    mean_total_return: 0.1,
    median_total_return: 0.1,
    stdev_total_return: 0.0,
    p_negative: 0.0,
    p_ruined: 0.0,
    total_return_histogram: { edges: [0, 1], counts: [1] },
    r_multiple_histogram: { edges: [-1, 2], counts: [1] },
    expectancy: null,
  },
}

describe('BatchesList', () => {
  it('fetches batches on mount and renders one row per batch', async () => {
    listBatches.mockResolvedValueOnce(items)

    const wrapper = mount(BatchesList)
    await flushPromises()

    expect(listBatches).toHaveBeenCalledOnce()
    expect(wrapper.text()).toContain('fast period matters')
    expect(wrapper.text()).toContain('3')
  })

  it('emits select with the batch id when a row is clicked', async () => {
    listBatches.mockResolvedValueOnce(items)

    const wrapper = mount(BatchesList)
    await flushPromises()
    await wrapper.find('[data-testid="batch-row-1"]').trigger('click')

    expect(wrapper.emitted('select')).toEqual([[1]])
  })

  it('shows an empty state with no batches', async () => {
    listBatches.mockResolvedValueOnce([])

    const wrapper = mount(BatchesList)
    await flushPromises()

    expect(wrapper.text()).toContain('No batches yet.')
  })

  it('shows a validation error when base id or hypothesis is missing', async () => {
    listBatches.mockResolvedValueOnce([])

    const wrapper = mount(BatchesList)
    await flushPromises()
    await wrapper.find('[data-testid="batch-create-button"]').trigger('click')
    await flushPromises()

    expect(createBatch).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Fill in base experiment id and hypothesis')
  })

  it('shows an error for invalid grid JSON', async () => {
    listBatches.mockResolvedValueOnce([])

    const wrapper = mount(BatchesList)
    await flushPromises()
    await wrapper.find('[data-testid="batch-base-id"]').setValue(1)
    await wrapper.find('[data-testid="batch-hypothesis"]').setValue('h')
    await wrapper.find('[data-testid="batch-grid"]').setValue('not json')
    await wrapper.find('[data-testid="batch-create-button"]').trigger('click')
    await flushPromises()

    expect(createBatch).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('valid JSON')
  })

  it('creates a batch and refreshes the list', async () => {
    listBatches.mockResolvedValueOnce([]).mockResolvedValueOnce(items)
    getExperiment.mockResolvedValueOnce(baseExperiment)
    createBatch.mockResolvedValueOnce({ id: 1, hypothesis: 'h', notes: null, created_at: '', experiments: [] })

    const wrapper = mount(BatchesList)
    await flushPromises()
    await wrapper.find('[data-testid="batch-base-id"]').setValue(1)
    await wrapper.find('[data-testid="batch-hypothesis"]').setValue('fast period matters')
    await wrapper.find('[data-testid="batch-grid"]').setValue('{"strategy.fast_period": [8, 10]}')
    await wrapper.find('[data-testid="batch-create-button"]').trigger('click')
    await flushPromises()

    expect(getExperiment).toHaveBeenCalledWith(1)
    expect(createBatch).toHaveBeenCalledWith(
      expect.objectContaining({
        hypothesis: 'fast period matters',
        base: baseExperiment.spec,
        grid: { 'strategy.fast_period': [8, 10] },
      }),
    )
    expect(listBatches).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('fast period matters')
  })
})
