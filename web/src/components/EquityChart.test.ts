import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EquityPoint } from '../types'

const chartInstances: Array<{ config: unknown; destroy: () => void }> = []

vi.mock('chart.js/auto', () => {
  class FakeChart {
    config: unknown
    destroy = vi.fn()
    constructor(_canvas: unknown, config: unknown) {
      this.config = config
      chartInstances.push(this)
    }
  }
  return { Chart: FakeChart }
})

const { default: EquityChart } = await import('./EquityChart.vue')

const points: EquityPoint[] = [
  { index: 0, equity: 10_000, drawdown: 0 },
  { index: 1, equity: 10_200, drawdown: 0 },
  { index: 2, equity: 10_098, drawdown: 0.01 },
]

describe('EquityChart', () => {
  beforeEach(() => {
    chartInstances.length = 0
  })

  it('renders a canvas and builds a line chart from the equity points', () => {
    const wrapper = mount(EquityChart, { props: { points } })

    expect(wrapper.find('canvas').exists()).toBe(true)
    expect(chartInstances).toHaveLength(1)
    const config = chartInstances[0].config as {
      type: string
      data: { labels: number[]; datasets: Array<{ data: number[] }> }
    }
    expect(config.type).toBe('line')
    expect(config.data.labels).toEqual([0, 1, 2])
    expect(config.data.datasets[0].data).toEqual([10_000, 10_200, 10_098])
  })

  it('rebuilds the chart when points change', async () => {
    const wrapper = mount(EquityChart, { props: { points } })

    await wrapper.setProps({ points: [{ index: 0, equity: 5_000, drawdown: 0 }] })

    expect(chartInstances).toHaveLength(2)
    expect(chartInstances[0].destroy).toHaveBeenCalled()
  })

  it('destroys the chart on unmount', () => {
    const wrapper = mount(EquityChart, { props: { points } })

    wrapper.unmount()

    expect(chartInstances[0].destroy).toHaveBeenCalled()
  })
})
