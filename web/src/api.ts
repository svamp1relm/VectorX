// Thin HTTP client for the VectorX API (api/main.py). No computation here —
// only fetch + JSON parsing; the backend computes everything.

import type {
  EquityPoint,
  ExperimentDetail,
  ExperimentSummaryItem,
  RunResult,
} from './types'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://127.0.0.1:8000'

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) {
    throw new Error(`VectorX API request failed: ${response.status} ${path}`)
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

export function getEquity(id: number, runId = 0): Promise<EquityPoint[]> {
  return getJson<EquityPoint[]>(`/experiments/${id}/equity?run_id=${runId}`)
}
