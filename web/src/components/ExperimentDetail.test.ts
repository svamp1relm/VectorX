import { flushPromises, shallowMount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import type { EquityPoint, ExperimentDetail as ExperimentDetailType, RunResult } from '../types'

const getExperiment = vi.fn()
const getResults = vi.fn()
const getEquity = vi.fn()
vi.mock('../api', () => ({
  getExperiment: (...args: unknown[]) => getExperiment(...args),
  getResults: (...args: unknown[]) => getResults(...args),
  getEquity: (...args: unknown[]) => getEquity(...args),
}))

const { default: ExperimentDetail } = await import('./ExperimentDetail.vue')

const detail: ExperimentDetailType = {
  id: 1,
  name: 'baseline_expectancy',
  seed: 42,
  runs: 2,
  status: 'completed',
  created_at: '2026-09-22T00:00:00Z',
  duration: 0.01,
  experiment_version: 1,
  code_version: 'unknown',
  spec: {
    name: 'baseline_expectancy',
    seed: 42,
    runs: 2,
    model: { p_win: 0.55, win_r: 2.0, loss_r: -1.0, n_trades: 20 },
    portfolio: { initial_capital: 10_000, risk_per_trade: 0.01, commission: 0, slippage: 0 },
    storage: { store_trades: false },
  },
  summary: {
    runs: 2,
    mean_total_return: 0.2,
    median_total_return: 0.2,
    stdev_total_return: 0.05,
    p_negative: 0.0,
    p_ruined: 0.0,
    total_return_histogram: { edges: [0, 1], counts: [2] },
    r_multiple_histogram: { edges: [-1, 2], counts: [1, 1] },
  },
}

const results: RunResult[] = [
  {
    run_index: 0,
    derived_seed: 1,
    metrics: {
      trades: 20,
      wins: 11,
      losses: 9,
      win_rate: 0.55,
      avg_win: 2,
      avg_loss: -1,
      expectancy_theoretical: 0.65,
      expectancy_sample: 0.6,
      total_return: 0.2,
      avg_trade: 5,
      variance: 2,
      stdev: 1.4,
      max_drawdown: 0.03,
      profit_factor: 2.2,
      ruined: false,
    },
  },
]

const equity: EquityPoint[] = [{ index: 0, equity: 10_000, drawdown: 0 }]

describe('ExperimentDetail', () => {
  it('loads experiment/results/equity for the given id and renders parameters and summary', async () => {
    getExperiment.mockResolvedValueOnce(detail)
    getResults.mockResolvedValueOnce(results)
    getEquity.mockResolvedValueOnce(equity)

    const wrapper = shallowMount(ExperimentDetail, { props: { id: 1 } })
    await flushPromises()

    expect(getExperiment).toHaveBeenCalledWith(1)
    expect(getResults).toHaveBeenCalledWith(1)
    expect(getEquity).toHaveBeenCalledWith(1)
    expect(wrapper.text()).toContain('baseline_expectancy')
    expect(wrapper.text()).toContain('0.55')
    expect(wrapper.text()).toContain('10000')
  })

  it('passes the equity curve and histograms down to the chart components', async () => {
    getExperiment.mockResolvedValueOnce(detail)
    getResults.mockResolvedValueOnce(results)
    getEquity.mockResolvedValueOnce(equity)

    const wrapper = shallowMount(ExperimentDetail, { props: { id: 1 } })
    await flushPromises()

    const equityChart = wrapper.findComponent({ name: 'EquityChart' })
    expect(equityChart.props('points')).toEqual(equity)
    const histogramCharts = wrapper.findAllComponents({ name: 'HistogramChart' })
    expect(histogramCharts).toHaveLength(2)
  })

  it('emits back when the back button is clicked', async () => {
    getExperiment.mockResolvedValueOnce(detail)
    getResults.mockResolvedValueOnce(results)
    getEquity.mockResolvedValueOnce(equity)

    const wrapper = shallowMount(ExperimentDetail, { props: { id: 1 } })
    await flushPromises()
    await wrapper.find('[data-testid="back-button"]').trigger('click')

    expect(wrapper.emitted('back')).toBeTruthy()
  })

  it('shows an error message when loading fails', async () => {
    getExperiment.mockRejectedValueOnce(new Error('boom'))
    getResults.mockResolvedValueOnce([])
    getEquity.mockResolvedValueOnce([])

    const wrapper = shallowMount(ExperimentDetail, { props: { id: 1 } })
    await flushPromises()

    expect(wrapper.text()).toContain('boom')
  })
})
