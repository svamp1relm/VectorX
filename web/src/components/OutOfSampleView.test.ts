import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import type { ExperimentDetail, OutOfSampleResult } from '../types'

const getExperiment = vi.fn()
const runOutOfSample = vi.fn()
vi.mock('../api', () => ({
  getExperiment: (...args: unknown[]) => getExperiment(...args),
  runOutOfSample: (...args: unknown[]) => runOutOfSample(...args),
}))

const { default: OutOfSampleView } = await import('./OutOfSampleView.vue')

const historicalDetail: ExperimentDetail = {
  id: 1,
  name: 'ma_crossover_btc_1h',
  seed: 0,
  runs: 1,
  status: 'completed',
  created_at: '2026-10-02T00:00:00Z',
  duration: 0.01,
  experiment_version: 1,
  code_version: 'unknown',
  spec: {
    type: 'historical_backtest',
    name: 'ma_crossover_btc_1h',
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

const oosResult: OutOfSampleResult = {
  train: { name: 'x_train', seed: 0, runs: 1, status: 'completed', spec: historicalDetail.spec, summary: historicalDetail.summary },
  test: { name: 'x_test', seed: 0, runs: 1, status: 'completed', spec: historicalDetail.spec, summary: { ...historicalDetail.summary, mean_total_return: -0.05 } },
  comparison: {
    train: { value: 1.0, canonical_value: 1.0, source: 'historical_backtest', sample_size: 1 },
    test: { value: -0.5, canonical_value: -0.5, source: 'historical_backtest', sample_size: 1 },
    risk_compatibility: { compatible: true, same_risk_definition: true, reference_risk_fraction: 0.01, mismatches: [] },
    delta_train_test: 1.5,
    warnings: [],
  },
}

describe('OutOfSampleView', () => {
  it('runs out-of-sample validation and renders train/test/delta', async () => {
    getExperiment.mockResolvedValueOnce(historicalDetail)
    runOutOfSample.mockResolvedValueOnce(oosResult)

    const wrapper = mount(OutOfSampleView)
    await wrapper.find('[data-testid="oos-base-id"]').setValue(1)
    await wrapper.find('[data-testid="oos-train-start"]').setValue('2024-01-01T00:00:00+00:00')
    await wrapper.find('[data-testid="oos-train-end"]').setValue('2024-01-01T09:00:00+00:00')
    await wrapper.find('[data-testid="oos-test-start"]').setValue('2024-01-01T10:00:00+00:00')
    await wrapper.find('[data-testid="oos-test-end"]').setValue('2024-01-01T19:00:00+00:00')
    await wrapper.find('[data-testid="oos-run-button"]').trigger('click')
    await flushPromises()

    expect(getExperiment).toHaveBeenCalledWith(1)
    expect(runOutOfSample).toHaveBeenCalledWith(
      expect.objectContaining({ train_start: '2024-01-01T00:00:00+00:00' }),
    )
    expect(wrapper.find('[data-testid="oos-delta"]').text()).toContain('1.5')
  })

  it('shows an error when the base experiment is not a historical backtest', async () => {
    getExperiment.mockResolvedValueOnce({
      ...historicalDetail,
      spec: { type: 'monte_carlo', name: 'mc', seed: 1, runs: 1, model: { p_win: 0.5, win_r: 2, loss_r: -1, n_trades: 10, risk_unit_fraction: 0.01 }, portfolio: historicalDetail.spec.portfolio, storage: { store_trades: false } },
    })

    const wrapper = mount(OutOfSampleView)
    await wrapper.find('[data-testid="oos-base-id"]').setValue(1)
    await wrapper.find('[data-testid="oos-train-start"]').setValue('2024-01-01T00:00:00+00:00')
    await wrapper.find('[data-testid="oos-train-end"]').setValue('2024-01-01T09:00:00+00:00')
    await wrapper.find('[data-testid="oos-test-start"]').setValue('2024-01-01T10:00:00+00:00')
    await wrapper.find('[data-testid="oos-test-end"]').setValue('2024-01-01T19:00:00+00:00')
    await wrapper.find('[data-testid="oos-run-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('historical_backtest')
  })

  it('shows a validation error when dates are missing', async () => {
    getExperiment.mockClear()
    const wrapper = mount(OutOfSampleView)
    await wrapper.find('[data-testid="oos-base-id"]').setValue(1)
    await wrapper.find('[data-testid="oos-run-button"]').trigger('click')
    await flushPromises()

    expect(getExperiment).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Fill in train start/end')
  })
})
