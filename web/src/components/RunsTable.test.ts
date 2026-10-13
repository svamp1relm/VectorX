import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { RunResult } from '../types'
import RunsTable from './RunsTable.vue'

const results: RunResult[] = [
  {
    run_index: 0,
    derived_seed: 111,
    metrics: {
      trades: 20,
      wins: 11,
      losses: 9,
      win_rate: 0.55,
      avg_win: 2.0,
      avg_loss: -1.0,
      expectancy_theoretical: 0.65,
      expectancy_sample: 0.6,
      total_return: 0.12,
      avg_trade: 5.5,
      variance: 2.1,
      stdev: 1.45,
      max_drawdown: 0.03,
      profit_factor: 2.44,
      ruined: false,
    },
  },
  {
    run_index: 1,
    derived_seed: 222,
    metrics: {
      trades: 20,
      wins: 0,
      losses: 20,
      win_rate: 0.0,
      avg_win: 0.0,
      avg_loss: -1.0,
      expectancy_theoretical: 0.65,
      expectancy_sample: -1.0,
      total_return: -0.9,
      avg_trade: -10.0,
      variance: 0.0,
      stdev: 0.0,
      max_drawdown: 0.9,
      profit_factor: 'Infinity',
      ruined: true,
    },
  },
]

describe('RunsTable', () => {
  it('renders one row per run with key metrics', () => {
    const wrapper = mount(RunsTable, { props: { results } })

    const rows = wrapper.findAll('tbody tr')
    expect(rows).toHaveLength(2)
    expect(rows[0].text()).toContain('0')
    expect(rows[0].text()).toContain('20')
    expect(rows[0].text()).toContain('0.55')
    expect(rows[0].text()).toContain('0.12')
  })

  it('renders the ruined flag and string-encoded profit_factor as-is', () => {
    const wrapper = mount(RunsTable, { props: { results } })

    const rows = wrapper.findAll('tbody tr')
    expect(rows[1].text()).toContain('Infinity')
    expect(rows[1].text().toLowerCase()).toContain('true')
  })

  it('shows an empty state with no results', () => {
    const wrapper = mount(RunsTable, { props: { results: [] } })

    expect(wrapper.findAll('tbody tr')).toHaveLength(0)
    expect(wrapper.text()).toContain('No runs')
  })

  it('renders a historical backtest run with null expectancy_theoretical without crashing', () => {
    const historicalResults: RunResult[] = [
      { ...results[0], metrics: { ...results[0].metrics, expectancy_theoretical: null } },
    ]

    const wrapper = mount(RunsTable, { props: { results: historicalResults } })

    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
  })
})
