import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { compareExpectancy, listExperiments } from '../api'
import { usePreferences } from '../preferences'
import type { ExperimentDetail, ExpectancyComparisonResult } from '../types'
import ExpectancyComparison from './ExpectancyComparison.vue'

vi.mock('../api', () => ({
  listExperiments: vi.fn(),
  compareExpectancy: vi.fn(),
}))

const detail = {
  id: 1,
  name: 'MC',
  seed: 1,
  runs: 1,
  status: 'completed',
  created_at: '2026-01-01T00:00:00Z',
  duration: 1,
  experiment_version: 1,
  code_version: 'test',
  spec: {
    type: 'monte_carlo',
    name: 'MC',
    seed: 1,
    runs: 1,
    model: {
      p_win: 0.5,
      win_r: 2,
      loss_r: -1,
      n_trades: 10,
      risk_unit_fraction: 0.01,
    },
    portfolio: {
      initial_capital: 10_000,
      risk_per_trade: 0.01,
      commission: 0,
      slippage: 0,
    },
    storage: { store_trades: false },
  },
  summary: {
    runs: 1,
    mean_total_return: 0,
    median_total_return: 0,
    stdev_total_return: 0,
    p_negative: 0,
    p_ruined: 0,
    total_return_histogram: { edges: [], counts: [] },
    r_multiple_histogram: { edges: [], counts: [] },
    expectancy: null,
  },
} as ExperimentDetail

const comparison: ExpectancyComparisonResult = {
  estimates: {
    theoretical: {
      value: 0.5,
      canonical_value: 0.5,
      source: 'theoretical_model',
      unit: 'R',
      sample_size: null,
      planned_sample_size: null,
      risk_definition: {
        unit: 'R',
        normalization_version: 'r-v1',
        method: 'model_r',
        risk_unit_fraction: 0.01,
        cost_basis: 'gross_r',
      },
    },
    sample: null,
    historical: {
      value: 0.5,
      canonical_value: 1,
      source: 'historical_backtest',
      unit: 'R',
      sample_size: 2,
      planned_sample_size: null,
      risk_definition: {
        unit: 'R',
        normalization_version: 'r-v1',
        method: 'entry_price_stop_loss_fraction',
        risk_unit_fraction: 0.02,
        cost_basis: 'gross_r',
      },
    },
  },
  risk_compatibility: {
    compatible: true,
    same_risk_definition: false,
    reference_risk_fraction: 0.01,
    mismatches: ['method', 'risk_unit_fraction'],
  },
  deltas: {
    delta_theoretical_sample: null,
    delta_theoretical_historical: -0.5,
    delta_sample_historical: null,
  },
  warnings: ['risk_definitions_converted'],
}

describe('ExpectancyComparison', () => {
  const preferences = usePreferences()

  beforeEach(() => {
    vi.mocked(listExperiments).mockResolvedValue([
      {
        id: 2,
        name: 'Historical',
        spec_type: 'historical_backtest',
        seed: 0,
        runs: 1,
        status: 'completed',
        created_at: '2026-01-01T00:00:00Z',
        experiment_version: 1,
        code_version: 'test',
        mean_total_return: 0,
        median_total_return: 0,
        stdev_total_return: 0,
        p_negative: 0,
        p_ruined: 0,
      },
    ])
    vi.mocked(compareExpectancy).mockResolvedValue(comparison)
    preferences.setLocale('en')
  })

  it('converts estimates and renders unavailable deltas as dashes', async () => {
    const wrapper = mount(ExpectancyComparison, { props: { detail } })
    await vi.waitFor(() =>
      expect(wrapper.findAll('[data-testid="comparison-counterpart"] option')).toHaveLength(1),
    )

    await wrapper.get('[data-testid="run-comparison"]').trigger('click')
    expect(compareExpectancy).toHaveBeenCalled()
    await vi.waitFor(() =>
      expect(wrapper.findAll('[data-testid="comparison-values"]')).toHaveLength(1),
    )

    expect(wrapper.text()).toContain('0.5')
    expect(wrapper.text()).toContain('1')
    expect(wrapper.text()).toContain('-0.5')
    expect(wrapper.text()).toContain('Risk definitions differ')
  })
})
