import { describe, expect, it, vi } from 'vitest'
import {
  compareExpectancy,
  getBlockBootstrap,
  getEquity,
  getExperiment,
  getResults,
  getRun,
  listExperiments,
  runSensitivity,
  runWalkForward,
} from './api'

function mockFetchOnce(body: unknown, ok = true, status = 200) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('api client', () => {
  it('listExperiments calls GET /experiments and returns parsed JSON', async () => {
    const fetchMock = mockFetchOnce([{ id: 1 }])

    const result = await listExperiments()

    expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/\/experiments$/))
    expect(result).toEqual([{ id: 1 }])
  })

  it('getExperiment calls GET /experiments/{id}', async () => {
    const fetchMock = mockFetchOnce({ id: 5 })

    await getExperiment(5)

    expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/\/experiments\/5$/))
  })

  it('getResults calls GET /experiments/{id}/results', async () => {
    const fetchMock = mockFetchOnce([])

    await getResults(7)

    expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/\/experiments\/7\/results$/))
  })

  it('getRun calls GET /experiments/{id}/runs/{run_id}', async () => {
    const fetchMock = mockFetchOnce({ run_index: 2 })

    await getRun(7, 2)

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/experiments\/7\/runs\/2$/),
    )
  })

  it('getEquity defaults run_id to 0', async () => {
    const fetchMock = mockFetchOnce([])

    await getEquity(3)

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/experiments\/3\/equity\?run_id=0$/),
    )
  })

  it('getEquity accepts an explicit run_id', async () => {
    const fetchMock = mockFetchOnce([])

    await getEquity(3, 4)

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/experiments\/3\/equity\?run_id=4$/),
    )
  })

  it('throws a clear error on a non-ok response', async () => {
    mockFetchOnce(null, false, 404)

    await expect(getExperiment(999)).rejects.toThrow('404')
  })

  it('compareExpectancy posts snake_case fields to the comparison endpoint', async () => {
    const fetchMock = mockFetchOnce({ estimates: {} })

    await compareExpectancy({
      monteCarloExperimentId: 1,
      historicalExperimentId: 2,
      referenceRiskFraction: 0.01,
    })

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/comparisons\/expectancy$/),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          monte_carlo_experiment_id: 1,
          historical_experiment_id: 2,
          reference_risk_fraction: 0.01,
        }),
      }),
    )
  })

  it('runSensitivity posts the sweep to the robustness endpoint', async () => {
    const fetchMock = mockFetchOnce({ points: [] })
    const payload = {
      hypothesis: 'test',
      base: { type: 'monte_carlo' },
      grid: { seed: [1, 2] },
    }

    await runSensitivity(payload as never)

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/robustness\/sensitivity$/),
      expect.objectContaining({ method: 'POST', body: JSON.stringify(payload) }),
    )
  })

  it('runWalkForward posts window durations to the robustness endpoint', async () => {
    const fetchMock = mockFetchOnce({ windows: [] })
    const payload = {
      base: { type: 'historical_backtest' },
      start: '2024-01-01T00:00:00+00:00',
      end: '2025-01-01T00:00:00+00:00',
      train_window_days: 90,
      test_window_days: 30,
      step_days: 30,
      reference_risk_fraction: 0.01,
    }

    await runWalkForward(payload as never)

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/robustness\/walk-forward$/),
      expect.objectContaining({ method: 'POST', body: JSON.stringify(payload) }),
    )
  })

  it('getBlockBootstrap maps request fields to query parameters', async () => {
    const fetchMock = mockFetchOnce({ confidence_interval: {} })

    await getBlockBootstrap(26, {
      blockSize: 20,
      seed: 7,
      confidence: 0.9,
      nResamples: 500,
    })

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(
        /\/experiments\/26\/robustness\/block-bootstrap\?block_size=20&seed=7&confidence=0\.9&n_resamples=500$/,
      ),
    )
  })
})
