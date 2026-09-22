import { describe, expect, it, vi } from 'vitest'
import {
  getEquity,
  getExperiment,
  getResults,
  getRun,
  listExperiments,
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
})
