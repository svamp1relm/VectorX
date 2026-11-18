import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePreferences } from '../preferences'
import type { ExperimentDetail, OutOfSampleResult } from '../types'

const getExperiment = vi.fn()
const runSensitivity = vi.fn()
const runWalkForward = vi.fn()
const getBlockBootstrap = vi.fn()
vi.mock('../api', () => ({
  getExperiment: (...args: unknown[]) => getExperiment(...args),
  runSensitivity: (...args: unknown[]) => runSensitivity(...args),
  runWalkForward: (...args: unknown[]) => runWalkForward(...args),
  getBlockBootstrap: (...args: unknown[]) => getBlockBootstrap(...args),
}))

const { default: RobustnessView } = await import('./RobustnessView.vue')

const historicalDetail: ExperimentDetail = {
  id: 26,
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
    storage: { store_trades: true },
  },
  summary: {
    runs: 1,
    mean_total_return: 0.1,
    median_total_return: 0.1,
    stdev_total_return: 0,
    p_negative: 0,
    p_ruined: 0,
    total_return_histogram: { edges: [0, 1], counts: [1] },
    r_multiple_histogram: { edges: [-1, 2], counts: [1] },
    expectancy: null,
  },
}

const comparison = {
  train: { value: 0.2, canonical_value: 0.2, source: 'historical_backtest', sample_size: 10 },
  test: { value: 0.1, canonical_value: 0.1, source: 'historical_backtest', sample_size: 5 },
  risk_compatibility: {
    compatible: true,
    same_risk_definition: true,
    reference_risk_fraction: 0.01,
    mismatches: [],
  },
  delta_train_test: 0.1,
  warnings: [],
}

const oosResult: OutOfSampleResult = {
  train: {
    name: 'train', seed: 0, runs: 1, status: 'completed',
    spec: historicalDetail.spec, summary: historicalDetail.summary,
  },
  test: {
    name: 'test', seed: 0, runs: 1, status: 'completed',
    spec: historicalDetail.spec, summary: historicalDetail.summary,
  },
  comparison,
}

beforeEach(() => {
  vi.clearAllMocks()
  usePreferences().setLocale('en')
})

describe('RobustnessView', () => {
  it('runs parameter sensitivity and renders result points', async () => {
    getExperiment.mockResolvedValueOnce(historicalDetail)
    runSensitivity.mockResolvedValueOnce({
      analysis_version: 1,
      points: [{ params: { 'strategy.fast_period': 8 }, expectancy_sample: 0.25, sharpe: 1.2 }],
    })
    const wrapper = mount(RobustnessView)
    await wrapper.get('[data-testid="robustness-base-id"]').setValue(26)
    await wrapper.get('[data-testid="sensitivity-grid"]').setValue('{"strategy.fast_period":[8]}')

    await wrapper.get('[data-testid="sensitivity-run"]').trigger('click')
    await flushPromises()

    expect(runSensitivity).toHaveBeenCalledWith({
      hypothesis: 'Sensitivity: btc_1h_ma_crossover',
      base: historicalDetail.spec,
      grid: { 'strategy.fast_period': [8] },
    })
    expect(wrapper.get('[data-testid="sensitivity-row"]').text()).toContain('0.25')
    expect(wrapper.get('[data-testid="sensitivity-row"]').text()).toContain('1.2')
  })

  it('rejects an invalid parameter grid without calling the API', async () => {
    const wrapper = mount(RobustnessView)
    await wrapper.get('[data-testid="robustness-base-id"]').setValue(26)
    await wrapper.get('[data-testid="sensitivity-grid"]').setValue('[]')

    await wrapper.get('[data-testid="sensitivity-run"]').trigger('click')
    await flushPromises()

    expect(runSensitivity).not.toHaveBeenCalled()
    expect(wrapper.get('[role="alert"]').text()).toContain('JSON object')
  })

  it('runs walk-forward and renders train/test expectancy', async () => {
    getExperiment.mockResolvedValueOnce(historicalDetail)
    runWalkForward.mockResolvedValueOnce({
      analysis_version: 1,
      windows: [{
        window: {
          train_start: '2024-01-01T00:00:00+00:00',
          train_end: '2024-02-01T00:00:00+00:00',
          test_start: '2024-02-01T00:00:00.000001+00:00',
          test_end: '2024-03-01T00:00:00+00:00',
        },
        result: oosResult,
      }],
    })
    const wrapper = mount(RobustnessView)
    await wrapper.get('[data-testid="robustness-base-id"]').setValue(26)
    await wrapper.get('[data-testid="walk-forward-start"]').setValue('2024-01-01T00:00:00+00:00')
    await wrapper.get('[data-testid="walk-forward-end"]').setValue('2025-01-01T00:00:00+00:00')

    await wrapper.get('[data-testid="walk-forward-run"]').trigger('click')
    await flushPromises()

    expect(runWalkForward).toHaveBeenCalledWith(expect.objectContaining({
      base: historicalDetail.spec,
      train_window_days: 365,
      test_window_days: 90,
      step_days: 90,
    }))
    const row = wrapper.get('[data-testid="walk-forward-row"]')
    expect(row.text()).toContain('0.2')
    expect(row.text()).toContain('0.1')
  })

  it('rejects walk-forward for a Monte Carlo experiment', async () => {
    getExperiment.mockResolvedValueOnce({
      ...historicalDetail,
      spec: {
        type: 'monte_carlo', name: 'mc', seed: 1, runs: 1,
        model: { p_win: 0.5, win_r: 2, loss_r: -1, n_trades: 10, risk_unit_fraction: 0.01 },
        portfolio: historicalDetail.spec.portfolio,
        storage: { store_trades: false },
      },
    })
    const wrapper = mount(RobustnessView)
    await wrapper.get('[data-testid="robustness-base-id"]').setValue(1)
    await wrapper.get('[data-testid="walk-forward-start"]').setValue('2024-01-01T00:00:00+00:00')
    await wrapper.get('[data-testid="walk-forward-end"]').setValue('2025-01-01T00:00:00+00:00')

    await wrapper.get('[data-testid="walk-forward-run"]').trigger('click')
    await flushPromises()

    expect(runWalkForward).not.toHaveBeenCalled()
    expect(wrapper.get('[role="alert"]').text()).toContain('historical_backtest')
  })

  it('runs block bootstrap and renders its confidence interval', async () => {
    getBlockBootstrap.mockResolvedValueOnce({
      analysis_version: 1,
      block_size: 20,
      confidence_interval: {
        point_estimate: 0.15, lower: -0.05, upper: 0.35, confidence: 0.95, n_resamples: 2000,
      },
    })
    const wrapper = mount(RobustnessView)
    await wrapper.get('[data-testid="robustness-base-id"]').setValue(26)

    await wrapper.get('[data-testid="block-bootstrap-run"]').trigger('click')
    await flushPromises()

    expect(getBlockBootstrap).toHaveBeenCalledWith(26, {
      blockSize: 20, seed: 0, confidence: 0.95, nResamples: 2000,
    })
    const result = wrapper.get('[data-testid="block-bootstrap-result"]')
    expect(result.text()).toContain('0.15')
    expect(result.text()).toContain('-0.05')
    expect(result.text()).toContain('0.35')
  })

  it('shows block bootstrap API errors', async () => {
    getBlockBootstrap.mockRejectedValueOnce(new Error('no raw trades to analyze'))
    const wrapper = mount(RobustnessView)
    await wrapper.get('[data-testid="robustness-base-id"]').setValue(26)

    await wrapper.get('[data-testid="block-bootstrap-run"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain('no raw trades')
  })
})
