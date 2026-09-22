import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import App from './App.vue'

vi.mock('./api', () => ({
  listExperiments: vi.fn().mockResolvedValue([]),
  getExperiment: vi.fn(),
  getResults: vi.fn(),
  getEquity: vi.fn(),
}))

describe('App', () => {
  it('shows the experiments list by default', () => {
    const wrapper = mount(App)

    expect(wrapper.findComponent({ name: 'ExperimentsList' }).exists()).toBe(true)
    expect(wrapper.findComponent({ name: 'ExperimentDetail' }).exists()).toBe(false)
  })

  it('shows experiment detail after a select event, with the chosen id', async () => {
    const wrapper = mount(App)

    await wrapper.findComponent({ name: 'ExperimentsList' }).vm.$emit('select', 7)

    const detail = wrapper.findComponent({ name: 'ExperimentDetail' })
    expect(detail.exists()).toBe(true)
    expect(detail.props('id')).toBe(7)
  })

  it('returns to the list after a back event', async () => {
    const wrapper = mount(App)
    await wrapper.findComponent({ name: 'ExperimentsList' }).vm.$emit('select', 7)

    await wrapper.findComponent({ name: 'ExperimentDetail' }).vm.$emit('back')

    expect(wrapper.findComponent({ name: 'ExperimentsList' }).exists()).toBe(true)
    expect(wrapper.findComponent({ name: 'ExperimentDetail' }).exists()).toBe(false)
  })
})
