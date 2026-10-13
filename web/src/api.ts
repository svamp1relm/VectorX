// Thin HTTP client for the VectorX API (api/main.py). No computation here —
// only fetch + JSON parsing; the backend computes everything.

import type {
  AnalysisResult,
  BatchCreateRequest,
  BatchDetail,
  BatchSummary,
  EquityPoint,
  ExperimentDetail,
  ExperimentSummaryItem,
  ExpectancyComparisonResult,
  OutOfSampleRequest,
  OutOfSampleResult,
  RunResult,
} from './types'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://127.0.0.1:8000'

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown } | null
    if (body && body.detail !== undefined) {
      return typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    }
  } catch {
    // response body wasn't JSON (or was empty); fall through to the generic message
  }
  return response.statusText || 'no error detail provided'
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) {
    throw new Error(`VectorX API request failed: ${response.status} ${path}: ${await parseErrorDetail(response)}`)
  }
  return (await response.json()) as T
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error(`VectorX API request failed: ${response.status} ${path}: ${await parseErrorDetail(response)}`)
  }
  return (await response.json()) as T
}

export function listExperiments(): Promise<ExperimentSummaryItem[]> {
  return getJson<ExperimentSummaryItem[]>('/experiments')
}

export function getExperiment(id: number): Promise<ExperimentDetail> {
  return getJson<ExperimentDetail>(`/experiments/${id}`)
}

export function getResults(id: number): Promise<RunResult[]> {
  return getJson<RunResult[]>(`/experiments/${id}/results`)
}

export function getRun(id: number, runId: number): Promise<RunResult> {
  return getJson<RunResult>(`/experiments/${id}/runs/${runId}`)
}

export function listBatches(): Promise<BatchSummary[]> {
  return getJson<BatchSummary[]>('/batches')
}

export function createBatch(payload: BatchCreateRequest): Promise<BatchDetail> {
  return postJson<BatchDetail>('/batches', payload)
}

export function getBatch(id: number): Promise<BatchDetail> {
  return getJson<BatchDetail>(`/batches/${id}`)
}

export function getAnalysis(id: number): Promise<AnalysisResult> {
  return getJson<AnalysisResult>(`/experiments/${id}/analysis`)
}

export function getEquity(id: number, runId = 0): Promise<EquityPoint[]> {
  return getJson<EquityPoint[]>(`/experiments/${id}/equity?run_id=${runId}`)
}

export function compareExpectancy(payload: {
  monteCarloExperimentId: number
  historicalExperimentId: number
  referenceRiskFraction: number
}): Promise<ExpectancyComparisonResult> {
  return postJson<ExpectancyComparisonResult>('/comparisons/expectancy', {
    monte_carlo_experiment_id: payload.monteCarloExperimentId,
    historical_experiment_id: payload.historicalExperimentId,
    reference_risk_fraction: payload.referenceRiskFraction,
  })
}

export function runOutOfSample(payload: OutOfSampleRequest): Promise<OutOfSampleResult> {
  return postJson<OutOfSampleResult>('/out-of-sample', payload)
}

export function exportUrl(id: number, format: 'json' | 'markdown'): string {
  return `${API_BASE}/experiments/${id}/export?format=${format}`
}
