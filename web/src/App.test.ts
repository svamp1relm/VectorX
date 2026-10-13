import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App.vue'
import { usePreferences } from './preferences'

vi.mock('./api', () => ({
  listExperiments: vi.fn().mockResolvedValue([]),
  getExperiment: vi.fn(),
  getResults: vi.fn(),
  getEquity: vi.fn(),
  getAnalysis: vi.fn(),
  compareExpectancy: vi.fn(),
  listBatches: vi.fn().mockResolvedValue([]),
  getBatch: vi.fn(),
  runOutOfSample: vi.fn(),
  exportUrl: vi.fn(() => 'http://example.com/export'),
}))

describe('App', () => {
  const preferences = usePreferences()

  beforeEach(() => {
    window.localStorage.clear()
    preferences.setLocale('en')
    preferences.setTheme('light')
  })

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

  it('switches to the batches view and back', async () => {
    const wrapper = mount(App)
    const viewSwitch = wrapper.get('[data-testid="view-switch"]')

    await viewSwitch.findAll('button')[1].trigger('click')

    expect(wrapper.findComponent({ name: 'BatchesList' }).exists()).toBe(true)
    expect(wrapper.findComponent({ name: 'ExperimentsList' }).exists()).toBe(false)

    await viewSwitch.findAll('button')[0].trigger('click')

    expect(wrapper.findComponent({ name: 'ExperimentsList' }).exists()).toBe(true)
  })

  it('switches the interface language between English and Russian', async () => {
    const wrapper = mount(App)
    const languageSwitch = wrapper.get('[data-testid="language-switch"]')

    expect(languageSwitch.text()).toContain('EN')
    expect(wrapper.text()).toContain('Experiments')

    await languageSwitch.findAll('button')[1].trigger('click')

    expect(wrapper.text()).toContain('Эксперименты')
    expect(window.localStorage.getItem('vectorx.locale')).toBe('ru')

    await languageSwitch.findAll('button')[0].trigger('click')

    expect(wrapper.text()).toContain('Experiments')
  })

  it('switches between light and dark themes', async () => {
    const wrapper = mount(App)
    const themeSwitch = wrapper.get('[data-testid="theme-switch"]')

    expect(document.documentElement.dataset.theme).toBe('light')

    await themeSwitch.findAll('button')[1].trigger('click')

    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(window.localStorage.getItem('vectorx.theme')).toBe('dark')

    await themeSwitch.findAll('button')[0].trigger('click')

    expect(document.documentElement.dataset.theme).toBe('light')
  })
})
