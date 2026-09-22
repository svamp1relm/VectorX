import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { HistogramBins } from '../types'

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

const { default: HistogramChart } = await import('./HistogramChart.vue')

const bins: HistogramBins = {
  edges: [0.0, 1.0, 2.0, 3.0],
  counts: [3, 5, 2],
}

describe('HistogramChart', () => {
  beforeEach(() => {
    chartInstances.length = 0
  })

  it('renders a bar chart with one label per bin, using edge midpoints', () => {
    const wrapper = mount(HistogramChart, { props: { bins } })

    expect(wrapper.find('canvas').exists()).toBe(true)
    expect(chartInstances).toHaveLength(1)
    const config = chartInstances[0].config as {
      type: string
      data: { labels: string[]; datasets: Array<{ data: number[] }> }
    }
    expect(config.type).toBe('bar')
    expect(config.data.labels).toHaveLength(3)
    expect(config.data.datasets[0].data).toEqual([3, 5, 2])
  })

  it('rebuilds the chart when bins change', async () => {
    const wrapper = mount(HistogramChart, { props: { bins } })

    await wrapper.setProps({ bins: { edges: [0, 1], counts: [7] } })

    expect(chartInstances).toHaveLength(2)
    expect(chartInstances[0].destroy).toHaveBeenCalled()
  })
})
